"""Application state service - Manages application-level runtime state"""

import asyncio
from typing import Optional
from models.animation_params.animation_param_id import AnimationParamID
from models.enums import ParamID, LogCategory, ZoneEditTarget
from models.domain.application import ApplicationState
from services.data_assembler import DataAssembler
from utils.logger import get_logger

log = get_logger().for_category(LogCategory.STATE)


class ApplicationStateService:
    """
    Manages application-level state (mode, selection, debugging, system config).

    This service follows the lightweight State-Only pattern - there is no
    ApplicationConfig because application state has no YAML configuration,
    only runtime state from state.json.

    Follows the same pattern as ZoneService and AnimationService:
    - Receives strongly typed domain object (ApplicationState) from DataAssembler
    - Provides high-level business operations
    - Delegates persistence to DataAssembler

    State categories:
    - Mode state: edit_mode, lamp_white_mode
    - Selection state: selected_zone_index, selected_param_id
    - Debugging: frame_by_frame_mode
    - System config: save_on_change
    """

    def __init__(self, assembler: DataAssembler):
        """
        Initialize application state service

        Args:
            assembler: DataAssembler instance for building and persisting state
        """
        self.assembler = assembler
        self.state: ApplicationState = assembler.build_application_state()

        # Debouncing: prevent IO thrashing on rapid state changes
        self._save_task: Optional[asyncio.Task] = None
        self._save_delay = 0.5  # 500ms debounce window

        # log.info(f"ApplicationStateService initialized: {self.state.edit_mode} mode")

    # === Internal Methods ===

    async def _debounced_save(self) -> None:
        """
        Internal: Debounced save implementation.

        Waits for debounce delay, then saves to disk.
        Called by _queue_save() after cancelling previous pending save.
        """
        await asyncio.sleep(self._save_delay)

        if not self.state.save_on_change:
            log.debug("Auto-save disabled, skipping state save")
            return

        try:
            self.assembler.save_application_state(self.state)
        except Exception as e:
            log.error(f"Failed to save application state: {e}")

    def _queue_save(self) -> None:
        """
        Queue a debounced save.

        Cancels any pending save task and schedules a new one.
        This prevents IO thrashing when state changes rapidly
        (e.g., encoder rotations, parameter adjustments).

        Only saves if save_on_change is True.
        """
        # Cancel previous pending save if any
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            log.debug("Cancelled previous pending save")

        # Schedule new save with debounce delay
        self._save_task = asyncio.create_task(self._debounced_save())
        log.debug(f"Queued state save (debounce: {self._save_delay*1000:.0f}ms)")

    # === Public API ===

    def get_state(self) -> ApplicationState:
        """
        Get current application state object

        Returns:
            ApplicationState instance
        """
        return self.state

    def save(self, **updates) -> None:
        """
        Update state fields and persist to disk with debouncing

        Quick-save shorthand. Accepts partial updates as keyword args.
        Only saves if save_on_change is True.

        Debounced: Rapid calls are batched and saved 500ms after the last call.

        Example:
            service.save(selected_zone_index=2, edit_mode=False)

        Args:
            **updates: Field name/value pairs to update
        """
        for key, value in updates.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
            else:
                log.error(f"Invalid ApplicationState field: {key}")
        self._queue_save()

    # === Mode Management ===

    def set_edit_mode(self, enabled: bool) -> None:
        """Set edit mode ON/OFF (debounced save)"""
        self.state.edit_mode = enabled
        self._queue_save()
        log.info(f"Edit mode set to: {self.state.edit_mode}")

    # === Selection Management ===
    def set_selected_animation_param_id(self, param: AnimationParamID) -> None:
        """
        Set currently selected animation parameter
        """
        self.state.selected_animation_param_id = param
        self._queue_save()
        log.info(f"Selected parameter id changed: {self.state.selected_animation_param_id.name}")

    def set_selected_param_id(self, param: ParamID) -> None:
        """
        Set currently active parameter (debounced save)

        Args:
            param: Parameter ID enum value
        """
        if not isinstance(param, ParamID):
            log.error(f"Invalid selected_param_id type: {type(param)}")
            return
        
        self.state.selected_param_id = param
        self._queue_save()
        log.info(f"Selected parameter id changed: {self.state.selected_param_id.name}")

    def set_selected_zone_index(self, index: int) -> None:
        """
        Set currently selected zone index (debounced save)

        Args:
            index: Zone index (0-based)
        """
        if not isinstance(index, int) or index < 0:
            log.error(f"Invalid selected_zone_index: {index}")
            return
        self.state.selected_zone_index = index
        self._queue_save()
        log.info(f"Zone index changed: {index}")

    
    def set_selected_zone_edit_target(self, zone_edit_target: ZoneEditTarget) -> None:
        self.state.selected_zone_edit_target = zone_edit_target
        self._queue_save()
        log.info(f"Selected zone edit target changed: {self.state.selected_zone_edit_target.name}")


    # === Debugging Features ===

    def toggle_frame_by_frame_mode(self) -> None:
        """Toggle frame-by-frame debugging mode ON/OFF (debounced save)"""
        self.state.frame_by_frame_mode = not self.state.frame_by_frame_mode
        self._queue_save()
        log.info(f"Frame-by-frame mode toggled: {self.state.frame_by_frame_mode}")

    # === System Configuration ===

    def set_save_on_change(self, enabled: bool) -> None:
        """
        Enable/disable auto-save on state changes

        Special case: always saves immediately (not debounced) since this is
        a critical setting that enables/disables the save functionality itself.

        Args:
            enabled: True to auto-save, False to disable
        """
        
        # Special case: always save this setting change immediately
        old_save_on_change = self.state.save_on_change
        self.state.save_on_change = True

        # Bypass debouncing for this critical setting
        try:
            self.assembler.save_application_state(self.state)
            log.info("Auto-save setting saved immediately (not debounced)")
        except Exception as e:
            log.error(f"Failed to save auto-save setting: {e}")

        self.state.save_on_change = enabled
        log.info(f"Auto-save {'enabled' if enabled else 'disabled'}")
