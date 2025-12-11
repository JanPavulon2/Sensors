import pytest
import asyncio
from models.enums import ZoneID, AnimationID, FramePriority, FrameSource
from models.color import Color
from engine.frame_manager import FrameManager
from animations.engine_v2 import AnimationEngine

class DummyZone:
    """Minimal stub for ZoneCombined"""
    def __init__(self, zid):
        self.id = zid
        self.state = type("State", (), {})()
        self.state.color = Color.from_rgb(100, 100, 100)
        self.config = type("Config", (), {})()
        self.config.id = zid
        
class DummyZoneService:
    def __init__(self):
        self.zones = {
            ZoneID.TOP: DummyZone(ZoneID.TOP),
            ZoneID.BOTTOM: DummyZone(ZoneID.BOTTOM)
        }
    def get_zone(self, zid):
        return self.zones[zid]

class DummyMapper:
    def all_zone_ids(self):
        return [ZoneID.TOP, ZoneID.BOTTOM]
    def get_zone_length(self, zone):
        return 3

class DummyStrip:
    def __init__(self):
        self.mapper = DummyMapper()
        self.shown = None
    def show_full_pixel_frame(self, frame):
        self.shown = frame

@pytest.mark.asyncio
async def test_animation_engine_starts_two_zones_and_both_emit_frames():
    fm = FrameManager(fps=240)
    strip = DummyStrip()
    fm.add_zone_strip(strip)

    zs = DummyZoneService()
    engine = AnimationEngine(fm, zs)

    # Start animations
    await engine.start_for_zone(
        ZoneID.TOP,
        AnimationID.BREATHE,
        {"speed": 80, "intensity": 100},
    )

    await engine.start_for_zone(
        ZoneID.BOTTOM,
        AnimationID.BREATHE,
        {"speed": 30, "intensity": 100},
    )

    # Let tasks emit a few frames
    await asyncio.sleep(0.05)

    # Assert both zones were rendered
    assert strip.shown is not None
    assert ZoneID.TOP in strip.shown
    assert ZoneID.BOTTOM in strip.shown

    top_pixels = strip.shown[ZoneID.TOP]
    bottom_pixels = strip.shown[ZoneID.BOTTOM]

    assert len(top_pixels) == 3
    assert len(bottom_pixels) == 3

    # Colors should not be black (animation ran)
    assert any(p.to_rgb() != (0,0,0) for p in top_pixels)
    assert any(p.to_rgb() != (0,0,0) for p in bottom_pixels)

    # Stop everything
    await engine.stop_all()
