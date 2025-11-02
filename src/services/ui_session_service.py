from dataclasses import dataclass, asdict
from typing import Optional
from models import MainMode, ParamID
from utils.logger import get_logger, LogCategory, LogLevel

log = get_logger()


@dataclass
class UISessionState:
    """Runtime UI/session state (non-domain state)"""
    main_mode: MainMode
    edit_mode: bool
    lamp_white_mode: bool
    lamp_white_saved_state: Optional[dict]
    current_param: ParamID
    current_zone_index: int


class UISessionService:
    """
    Manages user interface session state:
      - main_mode: STATIC / ANIMATION
      - edit_mode: editing on/off
      - lamp_white_mode: lamp white toggle
      - lamp_white_saved_state: previous lamp state for restore
      - current_param: which parameter is active
      - current_zone_index: which zone is currently selected
    """

    def __init__(self, assembler):
        self.assembler = assembler
        self.state: UISessionState = self._load_state()

    # === Internal ===

    def _load_state(self) -> UISessionState:
        """Load UI session state from assembler (state.json) with validation"""
        try:
            data = self.assembler.load_state()
        except Exception as e:
            log.error(LogCategory.STATE, f"Failed to load UI session state: {e}")
            # fallback to defaults
            return UISessionState(
                main_mode=MainMode.STATIC,
                edit_mode=True,
                lamp_white_mode=False,
                lamp_white_saved_state=None,
                current_param=ParamID.ZONE_COLOR_HUE,
                current_zone_index=0
            )

        try:
            main_mode_str = data.get("main_mode", "STATIC")
            main_mode = MainMode[main_mode_str] if main_mode_str in MainMode.__members__ else MainMode.STATIC

            current_param_str = data.get("active_parameter", "ZONE_COLOR_HUE")
            current_param = ParamID[current_param_str] if current_param_str in ParamID.__members__ else ParamID.ZONE_COLOR_HUE

            state = UISessionState(
                main_mode=main_mode,
                edit_mode=data.get("edit_mode_on", True),
                lamp_white_mode=data.get("lamp_white_mode_on", False),
                lamp_white_saved_state=data.get("lamp_white_saved_state", None),
                current_param=current_param,
                current_zone_index=int(data.get("selected_zone_index", 0)),
            )

            log.log(LogCategory.SYSTEM, "UI session state loaded", **asdict(state))
            return state

        except Exception as e:
            log.error(LogCategory.STATE, f"Failed to parse UI session state: {e}")
            # fallback defaults
            return UISessionState(
                main_mode=MainMode.STATIC,
                edit_mode=True,
                lamp_white_mode=False,
                lamp_white_saved_state=None,
                current_param=ParamID.ZONE_COLOR_HUE,
                current_zone_index=0
            )

    def _save_state(self):
        """Save current UI session state to state.json via assembler"""
        try:
            data = {
                "main_mode": self.state.main_mode.name,
                "edit_mode_on": self.state.edit_mode,
                "lamp_white_mode_on": self.state.lamp_white_mode,
                "lamp_white_saved_state": self.state.lamp_white_saved_state,
                "active_parameter": self.state.current_param.name,
                "selected_zone_index": self.state.current_zone_index,
            }

            self.assembler.save_partial_state(data)
            # Log only on LogLevel.DEBUG to reduce verbosity
            log.debug(LogCategory.STATE, f"UI saved: {self.state.main_mode.name}|{self.state.current_param.name}|Z{self.state.current_zone_index}")

        except Exception as e:
            log.error(LogCategory.STATE, f"Failed to save UI session state: {e}")

    def save(self, **updates):
        """
        Quick-save shorthand. Accepts partial updates as keyword args.
        Example:
            self.save(current_zone_index=2, edit_mode=False)
        """
        for key, value in updates.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self._save_state()
        
    # === Public API ===

    def get_state(self) -> UISessionState:
        """Return current UI state object"""
        return self.state

    def toggle_edit_mode(self):
        self.state.edit_mode = not self.state.edit_mode
        self._save_state()
        log.log(LogCategory.SYSTEM, "Edit mode toggled", edit_mode=self.state.edit_mode)

    def toggle_lamp_white_mode(self):
        self.state.lamp_white_mode = not self.state.lamp_white_mode
        self._save_state()
        log.log(LogCategory.SYSTEM, "Lamp white mode toggled", lamp_white_mode=self.state.lamp_white_mode)

    def set_main_mode(self, mode: MainMode):
        if not isinstance(mode, MainMode):
            log.error(f"Invalid main_mode type: {mode}")
            return
        self.state.main_mode = mode
        self._save_state()
        log.log(LogCategory.SYSTEM, "Main mode changed", main_mode=self.state.main_mode.name)

    def set_current_param(self, param: ParamID):
        if not isinstance(param, ParamID):
            log.error(f"Invalid current_param type: {param}")
            return
        self.state.current_param = param
        self._save_state()
        log.log(LogCategory.SYSTEM, "Active parameter changed", current_param=self.state.current_param.name)

    def set_current_zone_index(self, index: int):
        if not isinstance(index, int) or index < 0:
            log.error(LogCategory.STATE,f"Invalid current_zone_index: {index}")
            return
        self.state.current_zone_index = index
        self._save_state()
        log.log(LogCategory.SYSTEM, "Zone index changed", current_zone_index=index)

    def set_lamp_white_saved_state(self, saved: Optional[dict]):
        self.state.lamp_white_saved_state = saved
        self._save_state()
        log.log(LogCategory.SYSTEM, "Lamp white saved state updated", has_saved=bool(saved))
