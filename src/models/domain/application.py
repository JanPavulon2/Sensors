"""Application state domain model"""

from dataclasses import dataclass
from typing import Optional
from models.animation_params.animation_param_id import AnimationParamID
from models.enums import ZoneEditTarget


@dataclass
class ApplicationState:
    """
    Runtime application-level state from state.json

    This represents the overall application session state including:
    - Operating modes (STATIC/ANIMATION, edit mode, lamp white mode)
    - Current selection state (zone index, active parameter)
    - Debugging features (frame-by-frame mode)
    - System configuration (auto-save behavior)

    Unlike Zone/Animation domain models, there is no ApplicationConfig
    because application state has no YAML configuration - it's purely
    runtime state loaded from state.json.

    Default values defined here are the single source of truth used
    throughout the system (DataAssembler, fallback logic, etc.).
    """

    # === Mode State ===
    edit_mode: bool = True  # Enable/disable editing

    # === Selection State ===
    selected_zone_index: int = 0  
    selected_zone_edit_target: ZoneEditTarget = ZoneEditTarget.COLOR_HUE
    selected_animation_param_id: AnimationParamID = AnimationParamID.HUE
    
    # === Debugging Features ===
    frame_by_frame_mode: bool = False  # Frame-by-frame animation debugging

    # === System Configuration ===
    save_on_change: bool = True  # Auto-save state after every change
