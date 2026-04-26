import pytest
from models.color import Color
from models.enums import ZoneID, FramePriority, FrameSource
from models.frame import SingleZoneFrame, MultiZoneFrame, CompositeFrame


@pytest.mark.asyncio
async def test_singlezone_partial_merge(frame_manager, mock_zone_strip):
    # Initial state = black
    assert all(
        all(p.to_rgb() == (0, 0, 0) for p in zs.pixels)
        for zs in frame_manager.zone_render_states.values()
    )

    # Render frame that only updates TOP
    await frame_manager._render_frame(
        CompositeFrame(
            priority=FramePriority.MANUAL,
            ttl=1.0,
            source=FrameSource.MANUAL,
            updates={ZoneID.TOP: Color.red()}
        )
    )

    # TOP should be red
    top = frame_manager.zone_render_states[ZoneID.TOP].pixels
    assert all(p.to_rgb() == (255, 0, 0) for p in top)

    # BOTTOM should remain black (preserved from previous state)
    bottom = frame_manager.zone_render_states[ZoneID.BOTTOM].pixels
    assert all(p.to_rgb() == (0, 0, 0) for p in bottom)
