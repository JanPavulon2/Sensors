"""Tests for the WS281x-over-SPI output path (Raspberry Pi 5).

The bit encoding is the piece most likely to be wrong and the piece that cannot
be checked without an oscilloscope once it is on the wire, so it is tested here
as a pure function, with no SPI device involved.
"""

from hardware.led.spi_addressable_strip import (
    LATCH_RESET_BYTE_COUNT,
    SpiAddressableStrip,
    encode_pixels_to_spi_bytes,
)
from models.color import Color


def test_encodes_one_grb_pixel_as_three_spi_bytes_per_channel():
    """A WS281x bit becomes three SPI bits at 2.4 MHz: 0 -> 0b100, 1 -> 0b110.

    One 8-bit channel therefore occupies exactly three SPI bytes, and a pixel
    nine. Red (255, 0, 0) sent in GRB order puts the 0xFF byte second:

        G = 0x00 -> 100 100 100 100 100 100 100 100 -> 0x92 0x49 0x24
        R = 0xFF -> 110 110 110 110 110 110 110 110 -> 0xDB 0x6D 0xB6
        B = 0x00 -> 0x92 0x49 0x24
    """
    encoded = encode_pixels_to_spi_bytes([Color.from_rgb(255, 0, 0)], color_order="GRB")

    assert encoded == bytes(
        [0x92, 0x49, 0x24, 0xDB, 0x6D, 0xB6, 0x92, 0x49, 0x24]
    )


class RecordingSpiWriter:
    """Stands in for spidev at the one boundary that needs real hardware.

    Records what would go out on MOSI so the driver's framing can be asserted
    without a Raspberry Pi or a logic analyser attached.
    """

    def __init__(self) -> None:
        self.written: bytes = b""

    def write_bytes(self, payload: bytes) -> None:
        self.written = payload


def test_applying_a_frame_writes_pixels_followed_by_a_latch_reset():
    """WS281x latches a frame when the data line stays low long enough.

    Newer WS2812B revisions need roughly 280 us, so the driver pads every frame
    with 300 us of zero bytes - 90 bytes at the 2.4 MHz SPI clock.
    """
    spi_writer = RecordingSpiWriter()
    strip = SpiAddressableStrip(
        pixel_count=1,
        color_order="GRB",
        spi_writer=spi_writer,
    )

    strip.apply_frame([Color.from_rgb(255, 0, 0)])

    expected_pixels = bytes([0x92, 0x49, 0x24, 0xDB, 0x6D, 0xB6, 0x92, 0x49, 0x24])
    assert spi_writer.written == expected_pixels + bytes(LATCH_RESET_BYTE_COUNT)
    assert LATCH_RESET_BYTE_COUNT == 90


def _strip_with_recorder(pixel_count: int = 3) -> tuple:
    spi_writer = RecordingSpiWriter()
    strip = SpiAddressableStrip(
        pixel_count=pixel_count,
        color_order="GRB",
        spi_writer=spi_writer,
    )
    return strip, spi_writer


def test_set_pixel_buffers_without_touching_the_spi_device():
    """The interface promises set_pixel does not push; rendering is show()'s job.

    Writing per pixel would turn one 60 fps frame into as many SPI transfers as
    there are LEDs.
    """
    strip, spi_writer = _strip_with_recorder()

    strip.set_pixel(1, Color.from_rgb(0, 255, 0))

    assert spi_writer.written == b""
    assert strip.get_pixel(1).to_rgb() == (0, 255, 0)


def test_applying_a_short_frame_blacks_out_the_remaining_pixels():
    strip, _ = _strip_with_recorder(pixel_count=3)
    strip.set_pixel(2, Color.from_rgb(255, 255, 255))

    strip.apply_frame([Color.from_rgb(255, 0, 0)])

    assert strip.get_pixel(2).to_rgb() == (0, 0, 0)


def test_clear_blacks_the_buffer_and_pushes_it():
    strip, spi_writer = _strip_with_recorder(pixel_count=2)
    strip.apply_frame([Color.from_rgb(255, 0, 0), Color.from_rgb(0, 0, 255)])

    strip.clear()

    assert [pixel.to_rgb() for pixel in strip.get_frame()] == [(0, 0, 0), (0, 0, 0)]
    all_channels_dark = bytes([0x92, 0x49, 0x24] * 6)
    assert spi_writer.written == all_channels_dark + bytes(LATCH_RESET_BYTE_COUNT)
