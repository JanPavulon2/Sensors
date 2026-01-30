import pytest
from models.enums import ZoneID, FramePriority, FrameSource
from models.color import Color
from engine.frame_manager import FrameManager
from models.frame import MainStripFrame

@pytest.mark.asyncio
async def test_different_zones_update_independently():
    fm = FrameManager()

    # Dummy mapper: 2 zones, 3 pixels each
    class DummyMapper:
        def all_zone_ids(self):
            return [ZoneID.TOP, ZoneID.BOTTOM]
        def get_zone_length(self, zone_id):
            return 3

    class DummyStrip:
        def __init__(self): self.mapper = DummyMapper()
        def show_full_pixel_frame(self, frame): self.shown = frame

    strip = DummyStrip()
    fm.add_led_channel(strip)

    # initial state
    fm.zone_render_states[ZoneID.TOP].pixels = [
        Color.from_rgb(10,10,10),
        Color.from_rgb(10,10,10),
        Color.from_rgb(10,10,10)
    ]
    fm.zone_render_states[ZoneID.BOTTOM].pixels = [
        Color.from_rgb(20,20,20),
        Color.from_rgb(20,20,20),
        Color.from_rgb(20,20,20)
    ]

    # --- partial update from anim1 (TOP only)
    frame1 = MainStripFrame(
        priority=FramePriority.ANIMATION,
        ttl=2.0,
        source=FrameSource.ANIMATION,
        partial=True,
        updates={ ZoneID.TOP: Color.from_rgb(100,0,0) }
    )
    fm._render_frame(frame1)

    # --- partial update from anim2 (BOTTOM only)
    frame2 = MainStripFrame(
        priority=FramePriority.ANIMATION,
        ttl=2.0,
        source=FrameSource.ANIMATION,
        partial=True,
        updates={ ZoneID.BOTTOM: Color.from_rgb(0,100,0) }
    )
    fm._render_frame(frame2)

    out = strip.shown

    # TOP should be updated from frame1
    assert all(c.to_rgb() == (100,0,0) for c in out[ZoneID.TOP])

    # BOTTOM should be updated from frame2
    assert all(c.to_rgb() == (0,100,0) for c in out[ZoneID.BOTTOM])
