# components/zone_strip.py  (replace existing ZoneStrip class with this)

from typing import Dict, List, Tuple, Optional
from rpi_ws281x import PixelStrip, Color
from models.domain.zone import ZoneConfig
from models.enums import ZoneID
from infrastructure import GPIOManager
from utils.enum_helper import EnumHelper


class ZoneStrip:
    """
    Hardware abstraction for WS281x LED strip with zone-based control.

    Maintains:
      - zone_range: mapping zone_key -> (start_index, end_index)
      - zone_indices: mapping zone_key -> [abs_index0, abs_index1, ...]
      - zone_reversed: mapping zone_key -> bool
      - zone_colors cache

    All public APIs expect ZoneID enum zone identifiers.
    """

    def __init__(
        self,
        gpio: int,
        pixel_count: int,
        zones: List[ZoneConfig],
        gpio_manager: GPIOManager,
        color_order: Optional[int] = None,
        brightness: int = 255
    ) -> None:
        from rpi_ws281x import ws

        if color_order is None:
            color_order = ws.WS2811_STRIP_BRG  # Default for WS2811

        self.pixel_count: int = pixel_count

        # Register WS281x pin via GPIOManager
        gpio_manager.register_ws281x(
            pin=gpio,
            component=f"ZoneStrip(GPIO{gpio},{pixel_count}px)"
        )

        # Build both representations: range and explicit indices
        self.zone_range: Dict[str, Tuple[int, int]] = {}
        self.zone_indices: Dict[str, List[int]] = {}
        self.zone_reversed: Dict[str, bool] = {}

        for zone in zones:
            key = EnumHelper.to_string(zone.id)  # e.g. "FLOOR"
            start = zone.start_index
            end = zone.end_index
            # Normalize range (ensure start <= end)
            if start <= end:
                rng = (start, end)
                indices = list(range(start, end + 1))
            else:
                # Inverted config — still produce indices in physical order
                rng = (end, start)
                indices = list(range(end, start + 1))
            self.zone_range[key] = rng
            self.zone_indices[key] = indices
            self.zone_reversed[key] = bool(zone.reversed)

        # Cached colors (initialized to black)
        self.zone_colors: Dict[str, Tuple[int, int, int]] = {
            EnumHelper.to_string(zone.id): (0, 0, 0)
            for zone in zones
        }

        # PixelStrip constructor
        self.pixel_strip: PixelStrip = PixelStrip(
            pixel_count,    # num: total LED count
            gpio,           # pin: GPIO number
            800000,         # freq_hz: 800kHz signal frequency
            10,             # dma: DMA channel 10
            False,          # invert: normal signal (not inverted)
            brightness,     # brightness: 0-255 global brightness
            0,              # channel: PWM channel 0
            color_order     # strip_type
        )
        self.pixel_strip.begin()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def _validate_zone(self, zone_key: str) -> bool:
        return zone_key in self.zone_indices

    def _get_physical_pixel_index(self, zone_key: str, logical_index: int) -> int:
        """
        Convert logical pixel index (0..N-1 within zone) to absolute physical index.
        Accounts for reversed zones by mapping using zone_indices.
        """
        indices = self.zone_indices.get(zone_key)
        if indices is None:
            raise KeyError(f"Unknown zone: {zone_key}")

        zone_len = len(indices)
        if logical_index < 0 or logical_index >= zone_len:
            raise IndexError("logical_index out of range")

        # If zone is flagged reversed, logical 0 corresponds to last index in indices
        if self.zone_reversed.get(zone_key, False):
            return indices[-1 - logical_index]
        else:
            return indices[logical_index]

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    def show_full_pixel_frame(self, zone_pixels_dict: Dict[ZoneID, List[Tuple[int, int, int]]]) -> None:
        """
        Render full absolute frame to hardware.
        zone_pixels_dict: { ZoneID: [(r,g,b), ...], ... }
        Expectation: provided lists are per-zone logical arrays (length == zone length or shorter).
        """
        # Build full buffer
        full_buffer = [(0, 0, 0)] * self.pixel_count

        for zone_in, pixels in zone_pixels_dict.items():
            zone_key = zone_in.name
            if zone_key not in self.zone_indices:
                # unknown zone skip
                continue

            indices = self.zone_indices[zone_key]
            # When zone is reversed we still map logical 0..N-1 to physical indices accordingly
            if self.zone_reversed.get(zone_key, False):
                # map logical i -> indices[-1 - i]
                for i, color in enumerate(pixels):
                    if i < len(indices):
                        phys_idx = indices[-1 - i]
                        full_buffer[phys_idx] = color
            else:
                for i, color in enumerate(pixels):
                    if i < len(indices):
                        phys_idx = indices[i]
                        full_buffer[phys_idx] = color

        # Push buffer to hardware
        for idx, (r, g, b) in enumerate(full_buffer):
            # rpi_ws281x Color/PixelStrip expects Color or setPixelColorRGB depending on binding
            try:
                # Prefer setPixelColorRGB if available
                if hasattr(self.pixel_strip, "setPixelColorRGB"):
                    self.pixel_strip.setPixelColorRGB(idx, r, g, b)
                else:
                    self.pixel_strip.setPixelColor(idx, Color(r, g, b))
            except Exception:
                # Fallback to Color wrapper
                self.pixel_strip.setPixelColor(idx, Color(r, g, b))

        self.pixel_strip.show()

    def set_zone_color(self, zone: ZoneID, r: int, g: int, b: int, show: bool = True) -> None:
        zone_key = zone.name
        if not self._validate_zone(zone_key):
            return

        self.zone_colors[zone_key] = (r, g, b)

        indices = self.zone_indices[zone_key]
        color = Color(r, g, b)

        for phys in indices:
            if 0 <= phys < self.pixel_count:
                self.pixel_strip.setPixelColor(phys, color)

        if show:
            self.pixel_strip.show()

    def set_multiple_zones(self, zone_colors: Dict[ZoneID, Tuple[int, int, int]]) -> None:
        for zone_in, (r, g, b) in zone_colors.items():
            zone_key = zone_in.name
            if not self._validate_zone(zone_key):
                continue
            self.zone_colors[zone_key] = (r, g, b)
            indices = self.zone_indices[zone_key]
            color = Color(r, g, b)
            for phys in indices:
                if 0 <= phys < self.pixel_count:
                    self.pixel_strip.setPixelColor(phys, color)
        self.pixel_strip.show()

    def set_pixel_color(self, zone: ZoneID, pixel_index: int, r: int, g: int, b: int, show: bool = True) -> None:
        zone_key = zone.name
        if not self._validate_zone(zone_key):
            return

        try:
            phys = self._get_physical_pixel_index(zone_key, pixel_index)
        except (KeyError, IndexError):
            return

        self.pixel_strip.setPixelColor(phys, Color(r, g, b))

        if show:
            self.pixel_strip.show()

    def set_pixel_color_absolute(self, pixel_index: int, r: int, g: int, b: int, show: bool = False) -> None:
        if 0 <= pixel_index < self.pixel_count:
            self.pixel_strip.setPixelColor(pixel_index, Color(r, g, b))
            if show:
                self.pixel_strip.show()

    def show(self) -> None:
        self.pixel_strip.show()

    def clear(self) -> None:
        for i in range(self.pixel_count):
            self.pixel_strip.setPixelColor(i, Color(0, 0, 0))
        self.pixel_strip.show()
        # Reset cache
        for k in self.zone_colors.keys():
            self.zone_colors[k] = (0, 0, 0)

    # -----------------------------------------------------------------------
    # TransitionService helpers
    # -----------------------------------------------------------------------
    def get_frame(self) -> List[Tuple[int, int, int]]:
        frame = []
        for i in range(self.pixel_count):
            color: int = int(self.pixel_strip.getPixelColor(i))  # type: ignore
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            frame.append((r, g, b))
        return frame

    def get_zone_color(self, zone: ZoneID) -> Optional[Tuple[int, int, int]]:
        zone_key = zone.name
        return self.zone_colors.get(zone_key)

    def build_frame_from_zones(self, zone_colors: Dict[ZoneID, Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
        """Build pixel-level frame from given zone colors (for transitions)."""
        frame = [(0, 0, 0)] * self.pixel_count
        for zone_in, (r, g, b) in zone_colors.items():
            zone_key = zone_in.name
            if zone_key not in self.zone_indices:
                continue
            indices = self.zone_indices[zone_key]
            for phys in indices:
                if 0 <= phys < self.pixel_count:
                    frame[phys] = (r, g, b)
        return frame
