import pytest
from models.color import Color
from models.enums import ZoneID, FramePriority, FrameSource
from models.frame import SingleZoneFrame, MultiZoneFrame
from models.frame import MainStripFrame


@pytest.mark.asyncio
async def test_singlezone_partial_merge(frame_manager, mock_led_channel):
    # Initial state = black
    assert all(
        all(p.to_rgb() == (0, 0, 0) for p in zs.pixels)
        for zs in frame_manager.zone_render_states.values()
    )

    # Push partial frame
    f = SingleZoneFrame(
        priority=FramePriority.MANUAL,
        source=FrameSource.MANUAL,
        zone_id=ZoneID.TOP,
        color=Color.red(),
        partial=True
    )

    await frame_manager.push_frame(f)

    # Force one render tick
    await frame_manager._render_frame(
        MainStripFrame(
            priority=f.priority, ttl=f.ttl, source=f.source,
            partial=True, updates={ZoneID.TOP: Color.red()}
        )
    )

    # Verify merged output
    top = frame_manager.zone_render_states[ZoneID.TOP].pixels
    assert all(p.to_rgb() == (255, 0, 0) for p in top)

    bottom = frame_manager.zone_render_states[ZoneID.BOTTOM].pixels
    # untouched remains black
    assert all(p.to_rgb() == (0, 0, 0) for p in bottom)
