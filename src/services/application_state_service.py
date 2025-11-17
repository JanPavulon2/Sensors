"""Application state service - Manages application-level runtime state"""

from typing import Optional
from models.enums import MainMode, ParamID, LogCategory
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
    - Mode state: main_mode, edit_mode, lamp_white_mode
    - Selection state: current_zone_index, current_param
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

        log.info(f"ApplicationStateService initialized: {self.state.main_mode.name} mode")

    # === Internal Methods ===

    def _save(self) -> None:
        """
        Save current application state via assembler

        Only saves if save_on_change is True (allows disabling auto-save)
        """
        if not self.state.save_on_change:
            log.debug("Auto-save disabled, skipping state save")
            return

        try:
            self.assembler.save_application_state(self.state)
        except Exception as e:
            log.error(f"Failed to save application state: {e}")

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
        Update state fields and persist to disk

        Quick-save shorthand. Accepts partial updates as keyword args.
        Only saves if save_on_change is True.

        Example:
            service.save(current_zone_index=2, edit_mode=False)

        Args:
            **updates: Field name/value pairs to update
        """
        for key, value in updates.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
            else:
                log.error(f"Invalid ApplicationState field: {key}")
        self._save()

    # === Mode Management ===

    def set_edit_mode(self, enabled: bool) -> None:
        """Set edit mode ON/OFF"""
        self.state.edit_mode = enabled
        self._save()
        log.info(f"Edit mode set to: {self.state.edit_mode}")

    def set_lamp_white_mode(self, enabled: bool) -> None:
        """Set lamp white mode ON/OFF"""
        self.state.lamp_white_mode = enabled
        self._save()
        log.info(f"Lamp white mode set to: {self.state.lamp_white_mode}")

    def set_main_mode(self, mode: MainMode) -> None:
        """
        Set main operating mode

        Args:
            mode: MainMode.STATIC or MainMode.ANIMATION
        """
        
        self.state.main_mode = mode
        self._save()
        log.info(f"Main mode changed: {self.state.main_mode.name}")

    # === Selection Management ===

    def set_current_param(self, param: ParamID) -> None:
        """
        Set currently active parameter

        Args:
            param: Parameter ID enum value
        """
        if not isinstance(param, ParamID):
            log.error(f"Invalid current_param type: {type(param)}")
            return
        self.state.current_param = param
        self._save()
        log.info(f"Active parameter changed: {self.state.current_param.name}")

    def set_current_zone_index(self, index: int) -> None:
        """
        Set currently selected zone index

        Args:
            index: Zone index (0-based)
        """
        if not isinstance(index, int) or index < 0:
            log.error(f"Invalid current_zone_index: {index}")
            return
        self.state.current_zone_index = index
        self._save()
        log.info(f"Zone index changed: {index}")

    # === Lamp White Mode State ===

    def set_lamp_white_saved_state(self, saved: Optional[dict]) -> None:
        """
        Save/restore lamp state for lamp white mode

        Args:
            saved: Dictionary with saved lamp state or None to clear
        """
        self.state.lamp_white_saved_state = saved
        self._save()
        log.info(f"Lamp white saved state updated: {'saved' if saved else 'cleared'}")

    # === Debugging Features ===

    def toggle_frame_by_frame_mode(self) -> None:
        """Toggle frame-by-frame debugging mode ON/OFF"""
        self.state.frame_by_frame_mode = not self.state.frame_by_frame_mode
        self._save()
        log.info(f"Frame-by-frame mode toggled: {self.state.frame_by_frame_mode}")

    # === System Configuration ===

    def set_save_on_change(self, enabled: bool) -> None:
        """
        Enable/disable auto-save on state changes

        Args:
            enabled: True to auto-save, False to disable
        """
        # Special case: always save this setting change
        old_save_on_change = self.state.save_on_change
        self.state.save_on_change = True
        self._save()
        self.state.save_on_change = enabled
        log.info(f"Auto-save {'enabled' if enabled else 'disabled'}")
