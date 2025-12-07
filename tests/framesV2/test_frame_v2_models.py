from models.frame_v2 import SingleZoneFrame, MultiZoneFrame, PixelFrameV2
from models.enums import ZoneID, FramePriority, FrameSource
from models.color import Color


def test_single_zone_frame_update():
    f = SingleZoneFrame(
        priority=FramePriority.ANIMATION,
        source=FrameSource.ANIMATION,
        zone_id=ZoneID.TOP,
        color=Color.red()
    )
    assert f.as_zone_update() == {ZoneID.TOP: Color.red()}


def test_multi_zone_frame_update():
    f = MultiZoneFrame(
        priority=FramePriority.PULSE,
        source=FrameSource.PULSE,
        zone_colors={
            ZoneID.TOP: Color.green(),
            ZoneID.BOTTOM: Color.blue(),
        }
    )
    out = f.as_zone_update()
    assert out[ZoneID.TOP] == Color.green()
    assert out[ZoneID.BOTTOM] == Color.blue()


def test_pixel_frame_update():
    f = PixelFrameV2(
        priority=FramePriority.DEBUG,
        source=FrameSource.DEBUG,
        zone_pixels={
            ZoneID.BOTTOM: [Color.red(), Color.green()],
        }
    )
    out = f.as_zone_update()
    assert out[ZoneID.BOTTOM][0] == Color.red()
    assert out[ZoneID.BOTTOM][1] == Color.green()
