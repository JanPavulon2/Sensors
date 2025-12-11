import pytest
import asyncio
from models.enums import FramePriority, FrameSource, ZoneID
from models.color import Color
from models.frame_v2 import SingleZoneFrame
from engine.frame_manager import FrameManager


@pytest.mark.asyncio
async def test_frame_manager_accepts_singlezoneframe():
    fm = FrameManager(fps=60)

    frame = SingleZoneFrame(
        priority=FramePriority.ANIMATION,
        source=FrameSource.ANIMATION,
        zone_id=ZoneID.TOP,
        color=Color.from_rgb(10, 20, 30),
        partial=True,
    )

    await fm.push_frame(frame)

    # Frame should be in the ANIMATION priority queue
    q = fm.main_queues[FramePriority.ANIMATION.value]
    assert len(q) == 1

    stored = q[0]
    assert stored.priority == FramePriority.ANIMATION
    assert stored.source == FrameSource.ANIMATION
    assert stored.partial is True

    # Check update contents
    assert stored.updates[ZoneID.TOP] == Color.from_rgb(10, 20, 30)
