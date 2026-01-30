import pytest
from models.color import Color
from models.enums import ZoneID, FramePriority, FrameSource
from models.frame import MultiZoneFrame


@pytest.mark.asyncio
async def test_full_render_to_strip(frame_manager, mock_led_channel):
    f = MultiZoneFrame(
        priority=FramePriority.MANUAL,
        source=FrameSource.MANUAL,
        zone_colors={
            ZoneID.BOTTOM: Color.green(),
            ZoneID.TOP: Color.blue(),
        }
    )

    await frame_manager.push_frame(f)

    # select & render
    msf = await frame_manager._select_frame_by_priority()
    assert msf is not None

    frame_manager._render_frame(msf)

    # Verify mapper call
    mock_led_channel.show_full_pixel_frame.assert_called_once()

    sent = mock_led_channel.show_full_pixel_frame.call_args[0][0]

    assert all(c.to_rgb() == (0, 255, 0) for c in sent[ZoneID.BOTTOM])
    assert all(c.to_rgb() == (0, 0, 255) for c in sent[ZoneID.TOP])
