"""
Tests for partial frame support (Phase 3 foundation).

Tests that LedChannel properly handles frames that only update certain zones,
preserving pixels from previous frames for zones not included in partial frames.
"""

import pytest
from models.enums import ZoneID
from models.color import Color


class MockHardware:
    """Mock hardware for testing."""

    def __init__(self, pixel_count: int = 90):
        self.pixel_count = pixel_count
        self.pixels = [Color.black()] * pixel_count
        self.apply_count = 0

    def get_pixel(self, index: int) -> Color:
        """Get pixel color."""
        if 0 <= index < self.pixel_count:
            return self.pixels[index]
        return Color.black()

    def set_pixel(self, index: int, color: Color) -> None:
        """Set pixel color."""
        if 0 <= index < self.pixel_count:
            self.pixels[index] = color

    def apply_frame(self, frame: list) -> None:
        """Apply full frame."""
        self.apply_count += 1
        for i, color in enumerate(frame):
            if i < self.pixel_count:
                self.pixels[i] = color

    def show(self) -> None:
        """Flush to hardware."""
        pass


class MockZoneMapper:
    """Mock zone mapper for testing."""

    def __init__(self):
        self.zones = {
            ZoneID.FLOOR: (0, 30),  # Pixels 0-29
            ZoneID.LEFT: (30, 45),  # Pixels 30-44
            ZoneID.RIGHT: (45, 60),  # Pixels 45-59
            ZoneID.LAMP: (60, 90),  # Pixels 60-89
        }

    def all_zone_ids(self):
        return self.zones.keys()

    def get_indices(self, zone_id: ZoneID):
        """Get pixel indices for zone."""
        if zone_id not in self.zones:
            return []
        start, end = self.zones[zone_id]
        return list(range(start, end))

    def get_zone_length(self, zone_id: ZoneID):
        """Get pixel count for zone."""
        indices = self.get_indices(zone_id)
        return len(indices)


class MockLedChannel:
    """Mock LedChannel for testing partial frames."""

    def __init__(self):
        self.hardware = MockHardware(90)
        self.mapper = MockZoneMapper()
        self.pixel_count = 90

    def build_frame_from_zones(self, zone_colors: dict) -> list:
        """Build frame from zones (supports partial frames)."""
        # Start with existing pixels (preserves zones not in zone_colors)
        frame = [self.hardware.get_pixel(i) for i in range(self.pixel_count)]

        # Update only the zones provided in zone_colors
        for zone, color in zone_colors.items():
            indices = self.mapper.get_indices(zone)
            for phys_idx in indices:
                if 0 <= phys_idx < self.pixel_count:
                    frame[phys_idx] = color
        return frame

    def apply_pixel_frame(self, frame: list) -> None:
        """Apply pixel frame to hardware."""
        self.hardware.apply_frame(frame)


class TestPartialFrameSupport:
    """Test partial frame rendering."""

    def test_complete_frame_renders_all_zones(self):
        """Complete frame with all zones renders correctly."""
        strip = MockLedChannel()

        # Create complete frame (all zones)
        zone_colors = {
            ZoneID.FLOOR: Color.from_rgb(255, 0, 0),    # Red
            ZoneID.LEFT: Color.from_rgb(0, 255, 0),     # Green
            ZoneID.RIGHT: Color.from_rgb(0, 0, 255),    # Blue
            ZoneID.LAMP: Color.from_rgb(255, 255, 0),   # Yellow
        }

        frame = strip.build_frame_from_zones(zone_colors)

        # Verify all zones updated
        assert frame[0] == Color.from_rgb(255, 0, 0)    # FLOOR start
        assert frame[30] == Color.from_rgb(0, 255, 0)   # LEFT start
        assert frame[45] == Color.from_rgb(0, 0, 255)   # RIGHT start
        assert frame[60] == Color.from_rgb(255, 255, 0) # LAMP start

    def test_partial_frame_preserves_missing_zones(self):
        """Partial frame preserves pixels from previous frame for missing zones."""
        strip = MockLedChannel()

        # First, set all zones to black
        first_frame = strip.build_frame_from_zones({
            ZoneID.FLOOR: Color.black(),
            ZoneID.LEFT: Color.black(),
            ZoneID.RIGHT: Color.black(),
            ZoneID.LAMP: Color.black(),
        })
        strip.apply_pixel_frame(first_frame)

        # Verify hardware has black pixels
        assert strip.hardware.get_pixel(0) == Color.black()
        assert strip.hardware.get_pixel(30) == Color.black()

        # Now submit PARTIAL frame (only FLOOR)
        partial_frame = strip.build_frame_from_zones({
            ZoneID.FLOOR: Color.from_rgb(255, 0, 0),  # Red for FLOOR
            # LEFT, RIGHT, LAMP not specified
        })
        strip.apply_pixel_frame(partial_frame)

        # Verify FLOOR updated to red
        assert strip.hardware.get_pixel(0) == Color.from_rgb(255, 0, 0)
        assert strip.hardware.get_pixel(29) == Color.from_rgb(255, 0, 0)

        # Verify other zones stayed black (preserved)
        assert strip.hardware.get_pixel(30) == Color.black()
        assert strip.hardware.get_pixel(45) == Color.black()
        assert strip.hardware.get_pixel(60) == Color.black()

    def test_multiple_partial_frames_accumulate_changes(self):
        """Multiple partial frames accumulate changes without losing previous zones."""
        strip = MockLedChannel()

        # Start with all zones black
        initial = strip.build_frame_from_zones({
            ZoneID.FLOOR: Color.black(),
            ZoneID.LEFT: Color.black(),
            ZoneID.RIGHT: Color.black(),
            ZoneID.LAMP: Color.black(),
        })
        strip.apply_pixel_frame(initial)

        # Partial 1: Update FLOOR to red
        partial1 = strip.build_frame_from_zones({
            ZoneID.FLOOR: Color.from_rgb(255, 0, 0),
        })
        strip.apply_pixel_frame(partial1)
        assert strip.hardware.get_pixel(0) == Color.from_rgb(255, 0, 0)  # Red

        # Partial 2: Update LEFT to green (FLOOR should stay red)
        partial2 = strip.build_frame_from_zones({
            ZoneID.LEFT: Color.from_rgb(0, 255, 0),
        })
        strip.apply_pixel_frame(partial2)
        assert strip.hardware.get_pixel(0) == Color.from_rgb(255, 0, 0)   # Still red
        assert strip.hardware.get_pixel(30) == Color.from_rgb(0, 255, 0)  # Now green

        # Partial 3: Update RIGHT to blue (FLOOR and LEFT should be preserved)
        partial3 = strip.build_frame_from_zones({
            ZoneID.RIGHT: Color.from_rgb(0, 0, 255),
        })
        strip.apply_pixel_frame(partial3)
        assert strip.hardware.get_pixel(0) == Color.from_rgb(255, 0, 0)   # Still red
        assert strip.hardware.get_pixel(30) == Color.from_rgb(0, 255, 0)  # Still green
        assert strip.hardware.get_pixel(45) == Color.from_rgb(0, 0, 255)  # Now blue

    def test_overwrite_previous_partial_frame(self):
        """Partial frame can overwrite previously set zones."""
        strip = MockLedChannel()

        # Partial 1: Set FLOOR to red
        partial1 = strip.build_frame_from_zones({
            ZoneID.FLOOR: Color.from_rgb(255, 0, 0),
        })
        strip.apply_pixel_frame(partial1)
        assert strip.hardware.get_pixel(0) == Color.from_rgb(255, 0, 0)

        # Partial 2: Overwrite FLOOR to blue
        partial2 = strip.build_frame_from_zones({
            ZoneID.FLOOR: Color.from_rgb(0, 0, 255),
        })
        strip.apply_pixel_frame(partial2)
        assert strip.hardware.get_pixel(0) == Color.from_rgb(0, 0, 255)  # Changed to blue

    def test_empty_partial_frame_preserves_all(self):
        """Empty partial frame (no zones) preserves all pixels."""
        strip = MockLedChannel()

        # Set some pixels
        initial = strip.build_frame_from_zones({
            ZoneID.FLOOR: Color.from_rgb(255, 0, 0),
            ZoneID.LEFT: Color.from_rgb(0, 255, 0),
        })
        strip.apply_pixel_frame(initial)

        # Empty partial frame
        empty_partial = strip.build_frame_from_zones({})
        strip.apply_pixel_frame(empty_partial)

        # Everything should be preserved
        assert strip.hardware.get_pixel(0) == Color.from_rgb(255, 0, 0)
        assert strip.hardware.get_pixel(30) == Color.from_rgb(0, 255, 0)
