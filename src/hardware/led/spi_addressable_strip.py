"""
SpiAddressableStrip - WS281x over SPI (Raspberry Pi 5)
=====================================================
The classic rpi_ws281x driver reaches the LEDs through the PWM/DMA peripherals
of BCM2835/2711. The Raspberry Pi 5's BCM2712 moves GPIO behind the RP1 chip
and that path no longer exists, so on a Pi 5 the data line is driven from SPI
MOSI instead: the SPI clock runs at three times the WS281x bit rate and every
WS281x bit is sent as three SPI bits.
"""

from __future__ import annotations

from math import ceil
from typing import List, Protocol

from hardware.led.color_order import COLOR_ORDER_MAP
from hardware.led.strip_interface import IPhysicalStrip
from models.color import Color

try:
    import spidev  # type: ignore
except ImportError:
    spidev = None  # type: ignore

# One WS281x bit lasts 1.25 us. Clocking SPI at three times that rate lets one
# WS281x bit be expressed as three SPI bits, which is what makes the high/low
# ratio - and therefore the distinction between a 0 and a 1 - come out right.
SPI_BITS_PER_WS281X_BIT = 3
WS281X_SPI_CLOCK_HERTZ = 2_400_000

SPI_BIT_PATTERN_FOR_ZERO = 0b100
SPI_BIT_PATTERN_FOR_ONE = 0b110

SPI_BYTES_PER_COLOR_CHANNEL = 3


def _encode_color_channel(channel_value: int) -> bytes:
    """Expand one 8-bit colour channel into its three-bits-per-bit SPI form."""
    encoded_bits = 0

    for bit_index in range(7, -1, -1):
        source_bit = (channel_value >> bit_index) & 1
        pattern = SPI_BIT_PATTERN_FOR_ONE if source_bit else SPI_BIT_PATTERN_FOR_ZERO
        encoded_bits = (encoded_bits << SPI_BITS_PER_WS281X_BIT) | pattern

    return encoded_bits.to_bytes(SPI_BYTES_PER_COLOR_CHANNEL, "big")


def encode_pixels_to_spi_bytes(pixels: List[Color], color_order: str) -> bytes:
    """Encode a frame into the SPI payload a WS281x chain expects.

    Channel reordering follows the same convention as WS281xStrip: the map
    gives the wire position of each of red, green and blue.
    """
    red_position, green_position, blue_position = COLOR_ORDER_MAP[color_order.upper()]

    payload = bytearray()

    for pixel in pixels:
        red, green, blue = pixel.to_rgb()

        ordered_channels = [0, 0, 0]
        ordered_channels[red_position] = red
        ordered_channels[green_position] = green
        ordered_channels[blue_position] = blue

        for channel_value in ordered_channels:
            payload += _encode_color_channel(channel_value)

    return bytes(payload)


# A WS281x chain latches the frame it has just received once the data line has
# been held low long enough. Newer WS2812B revisions want roughly 280 us, well
# above the 50 us the original datasheet quoted, so the driver pads with 300 us
# of zero bytes rather than the shorter figure most examples use.
LATCH_RESET_MICROSECONDS = 300
LATCH_RESET_BYTE_COUNT = ceil(
    WS281X_SPI_CLOCK_HERTZ * LATCH_RESET_MICROSECONDS / 1_000_000 / 8
)


class SpiWriter(Protocol):
    """The single hardware boundary of this driver, injected so that framing
    can be tested without a real SPI device."""

    def write_bytes(self, payload: bytes) -> None:
        ...


class SpiAddressableStrip(IPhysicalStrip):
    """WS281x chain driven from SPI MOSI. Mirrors WS281xStrip's contract: the
    internal buffer is the source of truth and reads never touch hardware."""

    def __init__(
        self,
        pixel_count: int,
        color_order: str,
        spi_writer: SpiWriter,
    ) -> None:
        if color_order.upper() not in COLOR_ORDER_MAP:
            raise ValueError(f"Unsupported color order: {color_order}")

        self._pixel_count = pixel_count
        self._color_order = color_order.upper()
        self._spi_writer = spi_writer
        self._buffer: List[Color] = [Color.black() for _ in range(pixel_count)]

    @property
    def led_count(self) -> int:
        return self._pixel_count

    def apply_frame(self, pixels: List[Color]) -> None:
        """Atomic push of a whole frame: one encode, one SPI write."""
        length = min(len(pixels), self._pixel_count)

        for index in range(length):
            self._buffer[index] = pixels[index]

        # A frame shorter than the strip leaves the tail dark rather than
        # holding whatever it showed last.
        for index in range(length, self._pixel_count):
            self._buffer[index] = Color.black()

        self.show()

    def show(self) -> None:
        payload = encode_pixels_to_spi_bytes(self._buffer, self._color_order)
        self._spi_writer.write_bytes(payload + bytes(LATCH_RESET_BYTE_COUNT))

    def set_pixel(self, index: int, color: Color) -> None:
        """Buffer one pixel. Deliberately does not push - see show()."""
        if 0 <= index < self._pixel_count:
            self._buffer[index] = color

    def get_pixel(self, index: int) -> Color:
        if 0 <= index < self._pixel_count:
            return self._buffer[index]
        return Color.black()

    def get_frame(self) -> List[Color]:
        return self._buffer

    def clear(self) -> None:
        self._buffer = [Color.black() for _ in range(self._pixel_count)]
        self.show()


# MOSI pin of each SPI bus on the Raspberry Pi 5's 40-pin header. SPI0 is on by
# default (dtparam=spi=on); SPI1 needs dtoverlay=spi1-1cs in config.txt.
SPI_BUS_BY_MOSI_GPIO = {
    10: 0,
    20: 1,
}


class SpidevWriter:
    """Real SPI device. Thin on purpose - all framing lives in the strip, so
    this holds nothing worth testing without hardware attached."""

    def __init__(self, bus_number: int, device_number: int = 0) -> None:
        if spidev is None:
            raise RuntimeError("spidev is not installed")

        self._device = spidev.SpiDev()
        self._device.open(bus_number, device_number)
        self._device.max_speed_hz = WS281X_SPI_CLOCK_HERTZ
        self._device.mode = 0

    def write_bytes(self, payload: bytes) -> None:
        self._device.writebytes2(payload)

    def close(self) -> None:
        self._device.close()


def resolve_spi_bus_number(mosi_gpio_pin: int) -> int:
    """Map the configured MOSI pin to its SPI bus number."""
    if mosi_gpio_pin not in SPI_BUS_BY_MOSI_GPIO:
        supported = ", ".join(str(pin) for pin in sorted(SPI_BUS_BY_MOSI_GPIO))
        raise ValueError(
            f"GPIO {mosi_gpio_pin} is not an SPI MOSI pin. Addressable strips on "
            f"the SPI driver must be wired to one of: {supported}."
        )
    return SPI_BUS_BY_MOSI_GPIO[mosi_gpio_pin]
