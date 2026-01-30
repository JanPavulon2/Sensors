import asyncio
import pytest
from models.enums import ZoneID, AnimationID


@pytest.mark.asyncio
async def test_full_animation_pipeline(engine, frame_manager, mock_led_channel):
    # Start breathe animation
    await engine.start_for_zone(
        ZoneID.BOTTOM,
        AnimationID.BREATHE,
        {"speed": 100, "intensity": 100}
    )

    # Let it run a few frames
    await asyncio.sleep(0.05)

    # Verify some frames were pushed & rendered
    assert frame_manager.frames_rendered > 0

    # Verify strip got updates
    assert mock_led_channel.show_full_pixel_frame.called
