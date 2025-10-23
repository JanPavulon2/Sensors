"""
Zone Model

Represents a single LED zone with automatic index calculation.
"""

from dataclasses import dataclass
from typing import Optional

# Constant - WS2811 has 3 physical LEDs per addressable pixel
LEDS_PER_PIXEL = 3


@dataclass
class Zone:
    """
    Represents a single LED zone

    Attributes:
        name: Display name (e.g., "Lamp", "Top", "Bed Backlight") - user-friendly, capitalized
        tag: Technical identifier (e.g., "lamp", "top", "bed") - lowercase, used in code/state
        pixel_count: Number of addressable pixels in the zone
        enabled: Whether the zone is enabled for display/animation/etc 
        order: Order in the strip (1, 2, 3...) - for auto-calculating indices

    Calculated properties:
        total_leds: Total number of physical LEDs (pixel_count * LEDS_PER_PIXEL)
        start_index: Starting pixel index (calculated from order)
        end_index: Ending pixel index (start_index + pixel_count - 1)

    Example:
        zone = Zone(name="Lamp", tag="lamp", pixel_count=19, enabled=True, order=1)
        # total_leds = 57 (19 * 3)
        # After calculate_indices(): start_index=0, end_index=18
    """
    name: str           # Display name: "Lamp", "Top", "Bed Backlight"
    tag: str            # Technical ID: "lamp", "top", "bed"
    pixel_count: int    # Number of addressable pixels: 19, 4, 3...
    enabled: bool = True
    order: int = 0

    # Runtime - calculated by calculate_indices()
    start_index: int = 0
    end_index: int = 0

    @property
    def total_leds(self) -> int:
        """Total number of physical LEDs (pixel_count * LEDS_PER_PIXEL)"""
        return self.pixel_count * LEDS_PER_PIXEL

    def calculate_indices(self, previous_end_index: int):
        """
        Calculate start/end indices based on previous zone's end index

        Args:
            previous_end_index: End index of the previous zone (-1 if this is first zone)
        """
        if not self.enabled:
            self.start_index = -1
            self.end_index = -1
            return

        self.start_index = previous_end_index + 1 if previous_end_index >= 0 else 0
        self.end_index = self.start_index + self.pixel_count - 1

    def to_range(self) -> list:
        """
        Return zone as [start, end] range (old format for compatibility)

        Returns:
            [start_index, end_index] or None if disabled
        """
        if not self.enabled:
            return None
        return [self.start_index, self.end_index]

    def __str__(self):
        """String representation for debugging"""
        status = "[+]" if self.enabled else "[-]"
        return f"{status} [{self.tag:8}] {self.name:15} {self.total_leds:3} LEDs ({self.pixel_count:2}px) @ [{self.start_index:2}-{self.end_index:2}] order={self.order}"
