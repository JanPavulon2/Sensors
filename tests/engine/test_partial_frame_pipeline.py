import pytest
from models.color import Color
from models.enums import ZoneID


class MockZoneMapper:
    """Simple 4 zones: FLOOR=0..2, LEFT=3..4, RIGHT=5..6, LAMP=7..8"""
    ZONES = {
        ZoneID.FLOOR: list(range(0, 3)),
        ZoneID.LEFT:  list(range(3, 5)),
        ZoneID.RIGHT: list(range(5, 7)),
        ZoneID.LAMP:  list(range(7, 9)),
    }

    def all_zone_ids(self):
        return self.ZONES.keys()

    def get_indices(self, zone_id):
        return self.ZONES[zone_id]

    def get_zone_length(self, zone_id):
        return len(self.ZONES[zone_id])


class MockHardware:
    def __init__(self):
        self.pixels = [Color.black()] * 9
        self.applied_frames = 0

    def apply_frame(self, frame):
        self.pixels = list(frame)
        self.applied_frames += 1


class MockZoneStrip:
    """Minimal realistic ZoneStrip with partial update support."""

    def __init__(self):
        self.mapper = MockZoneMapper()
        self.hw = MockHardware()

    def build_frame(self, partial_zone_pixels):
        """partial_zone_pixels: {ZoneID: [Color,...]}"""

        # Start from existing buffer
        frame = list(self.hw.pixels)

        # Merge only given zones
        for zone_id, px_list in partial_zone_pixels.items():
            indices = self.mapper.get_indices(zone_id)
            for idx, phys in enumerate(indices):
                frame[phys] = px_list[idx]

        return frame

    def show_partial(self, partial_zone_pixels):
        frame = self.build_frame(partial_zone_pixels)
        self.hw.apply_frame(frame)

def test_partial_updates_single_zone():
    strip = MockZoneStrip()

    # initial: all black
    assert strip.hw.pixels == [Color.black()] * 9

    # update only FLOOR (3 px)
    strip.show_partial({
        ZoneID.FLOOR: [Color.red(), Color.red(), Color.red()],
    })

    assert strip.hw.pixels[0] == Color.red()
    assert strip.hw.pixels[1] == Color.red()
    assert strip.hw.pixels[2] == Color.red()

    # other zones untouched
    assert strip.hw.pixels[3] == Color.black()
    assert strip.hw.pixels[7] == Color.black()


def test_multiple_partial_updates_accumulate():
    strip = MockZoneStrip()

    strip.show_partial({
        ZoneID.FLOOR: [Color.red(), Color.red(), Color.red()],
    })
    strip.show_partial({
        ZoneID.LEFT: [Color.green(), Color.green()],
    })
    strip.show_partial({
        ZoneID.RIGHT: [Color.blue(), Color.blue()],
    })

    # Floor stays red
    assert strip.hw.pixels[0] == Color.red()
    # Left is green now
    assert strip.hw.pixels[3] == Color.green()
    # Right is blue now
    assert strip.hw.pixels[5] == Color.blue()
    # Lamp untouched
    assert strip.hw.pixels[7] == Color.black()


def test_partial_overwrite():
    strip = MockZoneStrip()

    strip.show_partial({
        ZoneID.FLOOR: [Color.red(), Color.red(), Color.red()],
    })

    strip.show_partial({
        ZoneID.FLOOR: [Color.blue(), Color.blue(), Color.blue()],
    })

    assert strip.hw.pixels[0] == Color.blue()


def test_partial_empty_does_nothing():
    strip = MockZoneStrip()

    strip.show_partial({
        ZoneID.LEFT: [Color.green(), Color.green()],
    })

    before = list(strip.hw.pixels)

    strip.show_partial({})

    assert strip.hw.pixels == before
