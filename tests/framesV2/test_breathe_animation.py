import pytest
from models.domain.parameter import ParameterCombined
from src.animations.breatheV2 import BreatheAnimationV2
from models.domain.zone import ZoneCombined, ZoneConfig, ZoneState
from models.enums import AnimationID, ParamID, ZoneID, ZoneRenderMode
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
                animation_id=AnimationID.BREATHE
        )

        
        parameters=dict[ParamID.ANIM_SPEED, ParameterCombined()]
        
        zone = ZoneCombined(
                config,
                state,
                parameters=dict
        )

        anim = BreatheAnimationV2(zone, speed=100, intensity=100)
        frame = await anim.step()

        assert frame.zone_id == ZoneID.TOP
        assert frame.color.brightness >= 0
        assert frame.color.brightness <= 100
