import pytest
from models.enums import ZoneID, FramePriority, FrameSource
from models.color import Color
from engine.frame_manager import FrameManager
from models.frame import CompositeFrame

@pytest.mark.asyncio
async def test_merge_preserves_untouched_zones():
    """
    When a CompositeFrame updates only one zone,
    other zones preserve their previous render state.
    """
    fm = FrameManager()

    class DummyMapper:
        def all_zone_ids(self):
            return [ZoneID.TOP, ZoneID.BOTTOM]
        def get_zone_length(self, zone_id):
            return 3

    class DummyStrip:
        def __init__(self):
            self.mapper = DummyMapper()
            self.shown = None
        def show_full_pixel_frame(self, frame):
            self.shown = frame

    strip = DummyStrip()
    fm.add_zone_strip(strip)

    # Set baseline state: TOP=black, BOTTOM=(5,5,5)
    fm.zone_render_states[ZoneID.TOP].pixels = [
        Color.from_rgb(0,0,0),
        Color.from_rgb(0,0,0),
        Color.from_rgb(0,0,0),
    ]
    fm.zone_render_states[ZoneID.BOTTOM].pixels = [
        Color.from_rgb(5,5,5),
        Color.from_rgb(5,5,5),
        Color.from_rgb(5,5,5),
    ]

    # Render a frame that only updates TOP
    frame = CompositeFrame(
        priority=FramePriority.ANIMATION,
        ttl=2,
        source=FrameSource.ANIMATION,
        updates={ ZoneID.TOP: Color.from_rgb(100, 100, 100) }
    )

    await fm._render_frame(frame)

    out = strip.shown
    assert out is not None

    # TOP should be updated to new color
    assert all(c.to_rgb() == (100,100,100) for c in out[ZoneID.TOP])

    # BOTTOM should be preserved (not blacked out)
    assert all(c.to_rgb() == (5,5,5) for c in out[ZoneID.BOTTOM])
