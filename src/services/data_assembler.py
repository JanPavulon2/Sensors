"""Data assembler - Loads config + state and builds domain objects"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from models.animation_params.animation_param_id import AnimationParamID
from models.enums import AnimationID, ZoneID, ZoneRenderMode
from models.domain import (
    AnimationConfig, AnimationState,
    ZoneConfig, ZoneState, ZoneCombined,
    ApplicationState
)
from models.color import Color
from managers import ConfigManager
from utils.serialization import Serializer
from models.enums import LogLevel
from utils.logger import get_logger, LogCategory
from lifecycle.task_registry import create_tracked_task, TaskCategory

log = get_logger().for_category(LogCategory.CONFIG)


class DataAssembler:
    """Assembles domain objects from existing managers + state"""

    def __init__(self, config_manager: ConfigManager, state_path: Path, debounce_ms: int = 500):
        self.config_manager = config_manager
        self.state_path = state_path
        self.color_manager = config_manager.color_manager
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
                # log.debug(f"Loaded state from {self.state_path}")
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
                log.debug(f"State saved {self.state_path}")
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

        # Schedule new save with debounce delay using normal asyncio task
        self._save_task = asyncio.create_task(self._debounced_save())

    def build_animations(self) -> List[AnimationConfig]:
        """Build animation config objects from YAML"""
        try:
            available_animations = self.animation_manager.get_all_animations()
            log.info(f"Loaded {len(available_animations)} animation definitions")
            return available_animations

        except Exception as e:
            log.error(f"Failed to build animations: {e}")
            raise

    def build_zones(self) -> List[ZoneCombined]:
        """
        Build zone domain objects from config + state.

        Preserves complete zone state including animation parameters
        for proper mode switching (STATIC ↔ ANIMATION) on app restart.
        """
        try:
            state_json = self.load_state()
            zones = []

            # IMPORTANT: Use get_all_zones() to preserve pixel indices for disabled zones
            zone_configs = self.config_manager.get_all_zones()  # Returns List[ZoneConfig] with indices calculated

            log.info(f"Building {len(zone_configs)} zone objects...")

            for zone_config in zone_configs:
                # Get state data using zone id (lowercase, e.g., "lamp" from ZoneID.LAMP)
                zone_key = zone_config.id.name.lower()
                zone_state_data = state_json.get("zones", {}).get(zone_key, {})

                if not zone_state_data:
                    log.warn(f"No state found for zone {zone_config.id.name}, using defaults")
                    color = Color.from_hue(0)
                    brightness = 100
                    mode = ZoneRenderMode.STATIC
                    animation_state = None
                else:
                    color_dict = zone_state_data.get("color", {"mode": "HUE", "hue": 0})
                    color = Color.from_dict(color_dict, self.color_manager)
                    brightness = int(zone_state_data.get("brightness", 100))
                    is_on = zone_state_data.get("is_on", True)

                    # Load zone mode with fallback to STATIC
                    try:
                        mode = Serializer.str_to_zone_render_mode(zone_state_data.get("mode", "STATIC"))
                        log.info(f"Zone {zone_config.id.name} mode={mode.name}")
                    except ValueError:
                        log.warn(f"Invalid mode for zone {zone_config.id.name}, using STATIC")
                        mode = ZoneRenderMode.STATIC

                    # Load animation state (preserved for mode switching)
                    animation_state = None
                    anim_data = zone_state_data.get("animation")
                    if anim_data:
                        anim_id_str = anim_data.get("id")
                        log.info(f"Zone {zone_config.id.name} has animation data: {anim_id_str}")
                        if anim_id_str:
                            try:
                                animation_id = Serializer.str_to_enum(anim_id_str, AnimationID)

                                # Load animation parameters
                                params_dict = anim_data.get("parameters", {})
                                animation_parameters = Serializer.animation_params_str_to_enum(params_dict) if params_dict else {}

                                # Create AnimationState object
                                animation_state = AnimationState(
                                    id=animation_id,
                                    parameter_values=animation_parameters
                                )
                            except ValueError:
                                log.warn(f"Invalid animation_id for zone {zone_config.id.name}: {anim_id_str}")

                zone_state = ZoneState(
                    id=zone_config.id,
                    color=color,
                    brightness=brightness,
                    is_on=is_on,
                    mode=mode,
                    animation=animation_state
                )

                zone_combined = ZoneCombined(
                    config=zone_config,
                    state=zone_state
                )

                zones.append(zone_combined)
                log.info(f"{zone_config.display_name} @ [{zone_config.start_index}-{zone_config.end_index}]")

            log.info(f"Successfully built {len(zones)} zones")
            return zones

        except Exception as e:
            log.error(f"Failed to build zones: {e}")
            raise

    def save_zone_state(self, zones: List[ZoneCombined]) -> None:
        """
        Save zone state to state.json.

        Preserves complete zone state including color and animation parameters
        for proper mode switching (STATIC ↔ ANIMATION) on app restart.
        """
        try:
            state_json = self.load_state()

            if "zones" not in state_json:
                state_json["zones"] = {}

            for zone in zones:
                zone_key = zone.config.id.name.lower()
                zone_data = {
                    "color": zone.state.color.to_dict(),
                    "brightness": zone.state.brightness,
                    "is_on": zone.state.is_on,
                    "mode": zone.state.mode.name  # Save zone mode (STATIC, ANIMATION)
                }

                # Save animation state if zone has animation settings
                # (even if mode=STATIC, for preservation when switching back to ANIMATION)
                if zone.state.animation:
                    zone_data["animation"] = {
                        "id": zone.state.animation.id.name,
                        "parameters": Serializer.animation_params_enum_to_str(zone.state.animation.parameter_values)
                    }

                state_json["zones"][zone_key] = zone_data

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

            # Parse enums with fallback to dataclass defaults
            try:
                param_str = app_data.get("selected_animation_parameter_id")
                selected_animation_param_id = Serializer.str_to_enum(param_str, AnimationParamID) if param_str else ApplicationState.selected_animation_param_id
            except ValueError:
                selected_animation_param_id = ApplicationState.selected_animation_param_id  # Dataclass default

            state = ApplicationState(
                edit_mode=app_data.get("edit_mode_on", ApplicationState.edit_mode),
                selected_zone_index=int(app_data.get("selected_zone_index", ApplicationState.selected_zone_index)),
                selected_animation_param_id=selected_animation_param_id,
                frame_by_frame_mode=app_data.get("frame_by_frame_mode", ApplicationState.frame_by_frame_mode),
                save_on_change=app_data.get("save_on_change", ApplicationState.save_on_change),
            )

            log.info(f"Built application state: zone_idx={state.selected_zone_index}")
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
                "selected_animation_param_id": Serializer.enum_to_str(app_state.selected_animation_param_id),
                "selected_zone_index": app_state.selected_zone_index,
                "selected_zone_edit_target": app_state.selected_zone_edit_target,
                "frame_by_frame_mode": app_state.frame_by_frame_mode,
                "save_on_change": app_state.save_on_change,
            }

            self.save_state(state_json)
            log.debug(f"Application state saved")

        except Exception as e:
            log.error(f"Failed to save application state: {e}")
            raise
