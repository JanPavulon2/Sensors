"""Data assembler - Loads config + state and builds domain objects"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from models.enums import ParamID, AnimationID, ZoneID, MainMode, ZoneMode
from models.domain import (
    ParameterConfig, ParameterState, ParameterCombined,
    AnimationConfig, AnimationState, AnimationCombined,
    ZoneConfig, ZoneState, ZoneCombined,
    ApplicationState
)
from models.color import Color
from managers import ConfigManager
from utils.enum_helper import EnumHelper
from models.enums import LogLevel
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.CONFIG)


class DataAssembler:
    """Assembles domain objects from existing managers + state"""

    def __init__(self, config_manager: ConfigManager, state_path: Path, debounce_ms: int = 500):
        self.config_manager = config_manager
        self.state_path = state_path
        self.color_manager = config_manager.color_manager
        self.parameter_manager = config_manager.parameter_manager
        self.animation_manager = config_manager.animation_manager

        # Debouncing: prevent IO thrashing on rapid state changes (all saves go through here)
        self._save_task: Optional[asyncio.Task] = None
        self._pending_state: Optional[dict] = None  # Latest state waiting to be saved
        self._save_delay = debounce_ms / 1000  # Convert to seconds

        log.info("DataAssembler initialized")

    def load_state(self) -> dict:
        """Load state from JSON file"""
        try:
            with open(self.state_path, "r") as f:
                state = json.load(f)
                log.debug(f"Loaded state from {self.state_path}")
                return state
        except FileNotFoundError:
            log.error(f"State file not found: {self.state_path}")
            raise
        except json.JSONDecodeError as e:
            log.warn(f"Invalid JSON in state file: {e}")
            raise

    def _write_state_to_disk(self, state: dict) -> None:
        """
        Internal: Actually write state to disk.

        Called after debounce delay. Uses latest pending state (not the
        state passed to save_state() call), ensuring we save final state.
        """
        try:
            with open(self.state_path, "w") as f:
                json.dump(state, f, indent=2)
                log.debug(f"Saved state to {self.state_path}")
        except Exception as e:
            log.error(f"Failed to save state: {e}")
            raise

    async def _debounced_save(self) -> None:
        """
        Internal: Debounced save implementation.

        Waits for debounce delay, then saves to disk ONLY IF _pending_state is not None.
        This ensures we skip intermediate saves and only write final state.
        """
        try:
            await asyncio.sleep(self._save_delay)

            # Only save if still pending (timer wasn't cancelled)
            if self._pending_state is None:
                return

            self._write_state_to_disk(self._pending_state)
            self._pending_state = None

        except asyncio.CancelledError:
            pass  # Timer was cancelled, don't save

    def save_state(self, state: dict) -> None:
        """
        Queue a debounced save of state to disk.

        Cancels any pending save timer and schedules a new one.
        This prevents IO thrashing when state changes rapidly
        (e.g., encoder rotations, parameter adjustments).

        Key behavior:
        - Rapid changes (10 encoder rotations in 100ms) → 1 disk write (not 10)
        - State is always up-to-date in memory
        - Disk write waits 500ms after LAST change, saves final state once
        """
        # Store latest state (will be saved after debounce delay)
        self._pending_state = state

        # Cancel previous pending save if any
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()

        # Schedule new save with debounce delay
        self._save_task = asyncio.create_task(self._debounced_save())

    def build_animations(self) -> List[AnimationCombined]:
        """Build animation domain objects from config + state"""
        try:
            state_json = self.load_state()
            animations = []

            param_configs = self.parameter_manager.get_all_parameters()
            available_animations = self.animation_manager.get_all_animations()

            log.info(f"Building {len(available_animations)} animation objects...")

            current_anim_id = state_json.get("current_animation", {}).get("id")
            current_anim_params = state_json.get("current_animation", {}).get("parameters", {})

            for anim_info in available_animations:
                animation_id = anim_info.id  # Already AnimationID enum
                parameter_ids = anim_info.get_all_parameters()

                animation_config = AnimationConfig(
                    id=animation_id,
                    tag=anim_info.tag,  # String tag for file/class lookup
                    display_name=anim_info.display_name,
                    description=anim_info.description,
                    parameters=parameter_ids
                )

                # Compare uppercase enum names (state.json now stores "SNAKE" not "snake")
                is_current = (current_anim_id == animation_id.name)

                # Extract parameter values from state
                param_values = {}
                if is_current:
                    for param_id in parameter_ids:
                        param_name = param_id.name
                        if param_name in current_anim_params:
                            param_values[param_id] = current_anim_params[param_name]

                animation_state = AnimationState(
                    id=animation_id,
                    enabled=is_current,
                    parameter_values=param_values
                )

                # Build parameter combined objects
                params_combined = {}
                for param_id in parameter_ids:
                    param_config = param_configs.get(param_id)
                    if not param_config:
                        log.warn(f"Parameter {param_id.name} not found in config, skipping")
                        continue

                    value = param_values.get(param_id, param_config.default)
                    param_state = ParameterState(id=param_id, value=value)
                    params_combined[param_id] = ParameterCombined(config=param_config, state=param_state)

                animation_combined = AnimationCombined(
                    config=animation_config,
                    state=animation_state,
                    parameters=params_combined
                )

                animations.append(animation_combined)
                log.info(f"  ✓ {animation_config.display_name} (current={is_current})")

            log.info(f"Successfully built {len(animations)} animations")
            return animations

        except Exception as e:
            log.error(f"Failed to build animations: {e}")
            raise

    def build_zones(self) -> List[ZoneCombined]:
        """Build zone domain objects from config + state"""
        try:
            state_json = self.load_state()
            zones = []

            param_configs = self.parameter_manager.get_all_parameters()
            # IMPORTANT: Use get_all_zones() to preserve pixel indices for disabled zones
            zone_configs = self.config_manager.get_all_zones()  # Returns List[ZoneConfig] with indices calculated

            log.info(f"Building {len(zone_configs)} zone objects...")

            for zone_config in zone_configs:
                # Get state data using zone tag (lowercase, e.g., "lamp")
                zone_state_data = state_json.get("zones", {}).get(zone_config.tag, {})

                if not zone_state_data:
                    log.warn(f"No state found for zone {zone_config.tag}, using defaults")
                    color = Color.from_hue(0)
                    brightness = 100
                    mode = ZoneMode.STATIC
                    animation_id = None
                else:
                    color_dict = zone_state_data.get("color", {"mode": "HUE", "hue": 0})
                    color = Color.from_dict(color_dict, self.color_manager)
                    brightness = zone_state_data.get("brightness", 100)

                    # Load zone mode using EnumHelper with fallback to STATIC
                    try:
                        mode = EnumHelper.to_enum(ZoneMode, zone_state_data.get("mode", "STATIC"))
                    except (ValueError, TypeError):
                        mode = ZoneMode.STATIC

                    # Load animation_id if zone is in ANIMATION mode
                    animation_id = None
                    if mode == ZoneMode.ANIMATION:
                        anim_id_str = zone_state_data.get("animation_id")
                        if anim_id_str:
                            try:
                                animation_id = EnumHelper.to_enum(AnimationID, anim_id_str)
                            except (ValueError, TypeError):
                                log.warn(f"Invalid animation_id for zone {zone_config.tag}: {anim_id_str}")

                zone_state = ZoneState(
                    id=zone_config.id,
                    color=color,
                    mode=mode,
                    animation_id=animation_id
                )

                params_combined = {}
                brightness_config = param_configs.get(ParamID.ZONE_BRIGHTNESS)
                if brightness_config:
                    brightness_state = ParameterState(id=ParamID.ZONE_BRIGHTNESS, value=brightness)
                    params_combined[ParamID.ZONE_BRIGHTNESS] = ParameterCombined(
                        config=brightness_config,
                        state=brightness_state
                    )

                zone_combined = ZoneCombined(
                    config=zone_config,
                    state=zone_state,
                    parameters=params_combined
                )

                zones.append(zone_combined)
                log.info(f"  ✓ {zone_config.display_name} @ [{zone_config.start_index}-{zone_config.end_index}]")

            log.info(f"Successfully built {len(zones)} zones")
            return zones

        except Exception as e:
            log.error(f"Failed to build zones: {e}")
            raise

    def save_animation_state(self, animations: List[AnimationCombined]) -> None:
        """Save current animation state to state.json"""
        try:
            state_json = self.load_state()

            current_anim = next((anim for anim in animations if anim.state.enabled), None)

            if current_anim:
                params_dict = {}
                for param_id, param_combined in current_anim.parameters.items():
                    params_dict[param_id.name] = param_combined.state.value

                state_json["current_animation"] = {
                    "id": current_anim.config.id.name,  # Keep enum name uppercase (e.g., "SNAKE")
                    "parameters": params_dict
                }
                log.debug(f"Saved anim state: {current_anim.config.display_name}")
            else:
                state_json["current_animation"] = {"id": None, "parameters": {}}
                log.debug("Saved anim state: none")

            self.save_state(state_json)

        except Exception as e:
            log.error(f"Failed to save animation state: {e}")
            raise

    def save_zone_state(self, zones: List[ZoneCombined]) -> None:
        """Save zone state to state.json"""
        try:
            state_json = self.load_state()

            if "zones" not in state_json:
                state_json["zones"] = {}

            for zone in zones:
                tag = zone.config.id.name.lower()
                zone_data = {
                    "color": zone.state.color.to_dict(),
                    "brightness": zone.brightness,  # Read from property (gets from parameters)
                    "mode": zone.state.mode.name  # Save zone mode (STATIC, ANIMATION, OFF)
                }

                # Save animation_id if zone is in ANIMATION mode
                if zone.state.animation_id:
                    zone_data["animation_id"] = zone.state.animation_id.name

                state_json["zones"][tag] = zone_data

            self.save_state(state_json)
            log.info(f"Successfully saved {len(zones)} zone states")

        except Exception as e:
            log.error(f"Failed to save zone state: {e}")
            raise

    def build_application_state(self) -> ApplicationState:
        """
        Build application state object from state.json

        Uses ApplicationState dataclass defaults as fallback values.

        Returns:
            ApplicationState with loaded or default values
        """
        try:
            state_json = self.load_state()
            app_data = state_json.get("application", {})

            if not app_data:
                log.warn("No application state found, using defaults")
                return ApplicationState()  # Use dataclass defaults

            # Parse enums using EnumHelper with fallback to dataclass defaults
            try:
                current_param = EnumHelper.to_enum(ParamID, app_data.get("active_parameter"))
            except (ValueError, TypeError):
                current_param = ApplicationState.current_param  # Dataclass default

            state = ApplicationState(
                edit_mode=app_data.get("edit_mode_on", ApplicationState.edit_mode),
                lamp_white_mode=app_data.get("lamp_white_mode_on", ApplicationState.lamp_white_mode),
                lamp_white_saved_state=app_data.get("lamp_white_saved_state", ApplicationState.lamp_white_saved_state),
                current_zone_index=int(app_data.get("selected_zone_index", ApplicationState.current_zone_index)),
                current_param=current_param,
                frame_by_frame_mode=app_data.get("frame_by_frame_mode", ApplicationState.frame_by_frame_mode),
                save_on_change=app_data.get("save_on_change", ApplicationState.save_on_change),
            )

            log.info(f"Built application state: zone_idx={state.current_zone_index}")
            return state

        except Exception as e:
            log.warn(f"Failed to build application state, using defaults: {e}")
            return ApplicationState()  # Use dataclass defaults

    def save_application_state(self, app_state: ApplicationState) -> None:
        """
        Save application state to state.json

        Args:
            app_state: ApplicationState instance to persist
        """
        try:
            state_json = self.load_state()

            state_json["application"] = {
                "edit_mode_on": app_state.edit_mode,
                "lamp_white_mode_on": app_state.lamp_white_mode,
                "lamp_white_saved_state": app_state.lamp_white_saved_state,
                "active_parameter": EnumHelper.to_string(app_state.current_param),
                "selected_zone_index": app_state.current_zone_index,
                "frame_by_frame_mode": app_state.frame_by_frame_mode,
                "save_on_change": app_state.save_on_change,
            }

            self.save_state(state_json)
            log.info(f"Saved application state")

        except Exception as e:
            log.error(f"Failed to save application state: {e}")
            raise
