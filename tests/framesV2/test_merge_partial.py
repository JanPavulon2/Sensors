import pytest
from models.enums import ZoneID, FramePriority, FrameSource
from models.color import Color
from engine.frame_manager import FrameManager
from models.frame import MainStripFrame

@pytest.mark.asyncio
async def test_partial_merge_keeps_other_zones_untouched():
    fm = FrameManager()

    # symulacja: mamy 2 strefy
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
    fm.add_led_channel(strip)

    # --- najpierw ustawiamy bazowy stan (jakby jakiś full frame był na starcie)
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

    # === wysyłamy partial update tylko dla TOP ===
    frame = MainStripFrame(
        priority=FramePriority.ANIMATION,
        ttl=2,
        source=FrameSource.ANIMATION,
        partial=True,
        updates={ ZoneID.TOP: Color.from_rgb(100, 100, 100) }
    )

    # render
    fm._render_frame(frame)

    out = strip.shown
    assert out is not None

    # TOP powinien być nadpisany na nowy kolor
    assert all(c.to_rgb() == (100,100,100) for c in out[ZoneID.TOP])

    # BOTTOM powinien zostać NIERUSZONY
    assert all(c.to_rgb() == (5,5,5) for c in out[ZoneID.BOTTOM])
