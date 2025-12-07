import pytest
from models.enums import ZoneID, AnimationID
from models.color import Color


@pytest.mark.asyncio
async def test_engine_starts_and_stops_zone(engine):
    params = {"speed": 90, "intensity": 80}

    await engine.start_for_zone(ZoneID.BOTTOM, AnimationID.BREATHE, params)

    assert ZoneID.BOTTOM in engine.tasks
    assert engine.active_anim_ids[ZoneID.BOTTOM] == AnimationID.BREATHE

    await engine.stop_for_zone(ZoneID.BOTTOM)

    assert ZoneID.BOTTOM not in engine.tasks