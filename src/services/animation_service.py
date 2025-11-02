"""Animation service - Business logic for animations"""

from typing import List, Optional
from models.enums import AnimationID, ParamID
from models.domain import AnimationCombined
from services.data_assembler import DataAssembler
from utils.logger import get_category_logger, LogCategory

log = get_category_logger(LogCategory.ANIMATION)


class AnimationService:
    """High-level animation operations"""

    def __init__(self, assembler: DataAssembler):
        self.assembler = assembler
        self.animations = assembler.build_animations()
        self._by_id = {anim.config.id: anim for anim in self.animations}

        self.available_ids: list[AnimationID] = list(self._by_id.keys())

        log(f"AnimationService initialized with {len(self.animations)} animations: {[a.name for a in self.available_ids]}")

    def get_animation(self, animation_id: AnimationID) -> AnimationCombined:
        """Get animation by ID"""
        return self._by_id[animation_id]

    def get_all(self) -> List[AnimationCombined]:
        """Get all animations"""
        return self.animations

    def get_current(self) -> Optional[AnimationCombined]:
        """Get currently enabled animation"""
        return next((anim for anim in self.animations if anim.state.enabled), None)

    def set_current(self, animation_id: AnimationID) -> AnimationCombined:
        """Set current animation (disables all others)"""
        for anim in self.animations:
            anim.state.enabled = (anim.config.id == animation_id)

        current = self.get_animation(animation_id)
        log.debug(f"AnimService: set current → {current.config.display_name}")
        self.save()
        return current

    def start(self, animation_id: AnimationID) -> AnimationCombined:
        """Start animation"""
        anim = self.get_animation(animation_id)
        if anim.start():
            self.save()
        return anim

    def stop(self, animation_id: AnimationID) -> AnimationCombined:
        """Stop animation"""
        anim = self.get_animation(animation_id)
        if anim.stop():
            self.save()
        return anim

    def stop_all(self) -> None:
        """Stop all animations"""
        for anim in self.animations:
            anim.state.enabled = False
        log("Stopped all animations")
        self.save()

    def adjust_parameter(self, animation_id: AnimationID, param_id: ParamID, delta: int) -> None:
        """Adjust animation parameter by delta steps"""
        anim = self.get_animation(animation_id)
        anim.adjust_param(param_id, delta)
        log(f"Adjusted {anim.config.display_name}.{param_id.name}: {anim.get_param_value(param_id)}")
        self.save()

    def set_parameter(self, animation_id: AnimationID, param_id: ParamID, value: any) -> None:
        """Set animation parameter value directly"""
        anim = self.get_animation(animation_id)
        anim.set_param_value(param_id, value)
        log(f"Set {anim.config.display_name}.{param_id.name} = {value}")
        self.save()

    def save(self) -> None:
        """Persist current state"""
        self.assembler.save_animation_state(self.animations)
