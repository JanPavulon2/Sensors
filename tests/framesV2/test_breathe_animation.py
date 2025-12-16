import pytest
from animations.breathe import BreatheAnimation
from models.domain.zone import ZoneCombined, ZoneConfig, ZoneState
from models.domain.animation import AnimationState
from models.enums import AnimationID, ZoneID, ZoneRenderMode
from models.color import Color


@pytest.mark.asyncio
async def test_breathe_animation_step_basic():
        config=ZoneConfig(
                id=ZoneID.TOP,
                display_name="TOP",
                pixel_count=4,
                enabled=True,
                reversed=False,
                order=1,
                start_index=0,
                end_index=4,
                gpio=18)

        state=ZoneState(
                id=ZoneID.TOP,
                color=Color.red(),
                mode=ZoneRenderMode.ANIMATION,
                animation=AnimationState(id=AnimationID.BREATHE)
        )


        zone = ZoneCombined(
                config,
                state
        )

        anim = BreatheAnimation(zone, speed=100, intensity=100)
        frame = await anim.step()

        assert frame.zone_id == ZoneID.TOP
        r, g, b = frame.color.to_rgb()
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255
