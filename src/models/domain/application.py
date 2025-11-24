"""Application state domain model"""

from dataclasses import dataclass
from typing import Optional
from models.enums import ParamID


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
    lamp_white_mode: bool = False  # Desk lamp mode (locks lamp to warm white)
    lamp_white_saved_state: Optional[dict] = None  # Saved state for lamp mode restore

    # === Selection State ===
    current_zone_index: int = 0  # Currently selected zone (for STATIC mode)
    current_param: ParamID = ParamID.ZONE_COLOR_HUE  # Currently active parameter

    # === Debugging Features ===
    frame_by_frame_mode: bool = False  # Frame-by-frame animation debugging

    # === System Configuration ===
    save_on_change: bool = True  # Auto-save state after every change
