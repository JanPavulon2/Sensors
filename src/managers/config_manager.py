"""
Config Manager

Main configuration manager with include system support.
Loads modular YAML files and initializes sub-managers.
"""

import yaml
from pathlib import Path
from typing import List, Optional, Dict, TYPE_CHECKING
from utils.logger import get_logger, get_category_logger, LogLevel, LogCategory

if TYPE_CHECKING:
    from models.zone import Zone

log = get_category_logger(LogCategory.CONFIG)

class ConfigManager:
    """
    Main configuration manager with include system support

    Loads config.yaml and processes include: directive to load modular YAML files.
    Initializes sub-managers (HardwareManager, ZoneManager, AnimationManager, ColorManager).

    Example:
        config = ConfigManager()
        config.load()

        # Access via properties (backward compatibility)
        hw_dict = config.hardware  # Returns dict
        zones_dict = config.zones  # Returns zone index dict

        # Access via sub-managers (new API)
        enc_cfg = config.hardware_manager.get_encoder("zone_selector")
        zone = config.zone_manager.get_zone("lamp")
        anim = config.animation_manager.get_animation("breathe")
    """

    def __init__(self, config_path="config/config.yaml", defaults_path="config/factory_defaults.yaml"):
        """
        Initialize ConfigManager

        Args:
            config_path: Path to main config.yaml (relative to src/)
            defaults_path: Path to factory defaults fallback
        """
        self.config_path = Path(config_path)
        self.factory_defaults_path = Path(defaults_path)
        self.data = {}

        # Sub-managers (initialized in load())
        self.hardware_manager = None
        self.zone_manager = None
        self.animation_manager = None
        self.color_manager = None
        self.parameter_manager = None

    def load(self):
        """
        Load YAML configuration with include system support

        Process:
        1. Load main config.yaml
        2. If it has 'include:' list, load and merge those files
        3. Otherwise treat as monolithic config (backward compatibility)
        4. Fallback to factory defaults.yaml on failure
        5. Initialize sub-managers

        Returns:
            Merged config data dict
        """
        try:
            # Resolve path relative to src/ directory
            src_dir = Path(__file__).parent.parent
            full_path = src_dir / self.config_path

            with open(full_path, "r", encoding="utf-8") as f:
                main_config = yaml.safe_load(f)

            # Check for include system
            if 'include' in main_config:
                log("Using include-based configuration")
                self.data = self._load_with_includes(main_config['include'], src_dir / self.config_path.parent)
            else:
                # Monolithic config (backward compatibility)
                log("Using monolithic configuration")
                self.data = main_config

        except Exception as ex:
            # Print traceback immediately to see the error
            import traceback
            print("="*80)
            print("CONFIG LOADING ERROR:")
            traceback.print_exc()
            print("="*80)

            log("Failed to load config.yaml", LogLevel.ERROR, error=str(ex), error_type=type(ex).__name__)
            log("Falling back to factory defaults", LogLevel.WARN)

            # Load factory defaults
            src_dir = Path(__file__).parent.parent
            defaults_path = src_dir / self.factory_defaults_path
            with open(defaults_path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f)

        # Initialize sub-managers
        self._initialize_managers()

        return self.data

    def _load_with_includes(self, include_list: List[str], config_dir: Path) -> Dict:
        """
        Load and merge multiple YAML files from include list

        Args:
            include_list: List of filenames to load (e.g., ["hardware.yaml", "zones.yaml"])
            config_dir: Directory containing config files

        Returns:
            Merged config dict
        """
        merged = {}

        for filename in include_list:
            filepath = config_dir / filename
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_data = yaml.safe_load(f)
                    if file_data:
                        merged.update(file_data)
                        log(f"Loaded {filename}", keys=str(list(file_data.keys())))
            except FileNotFoundError:
                log(f"File not found: {filename}", LogLevel.ERROR)
                raise
            except Exception as ex:
                log(f"Error loading {filename}", LogLevel.ERROR, error=str(ex))
                raise

        log("Config merge complete", total_keys=len(merged), keys=str(list(merged.keys())[:10]))
        return merged

    def _initialize_managers(self):
        """
        Initialize sub-managers with loaded config data

        Creates:
        - HardwareManager: GPIO pins, encoders, buttons, LED strips
        - ZoneManager: Zone collection with auto-calculated indices
        - AnimationManager: Animation metadata and parameters
        - ColorManager: Color preset definitions
        - ParameterManager: Parameter definitions and validation
        """
        from managers.hardware_manager import HardwareManager
        from managers.zone_manager import ZoneManager
        from managers.animation_manager import AnimationManager
        from managers.color_manager import ColorManager
        from managers.parameter_manager import ParameterManager

        # HardwareManager - inject merged config data
        try:
            self.hardware_manager = HardwareManager()
            self.hardware_manager.data = self.data
            self.hardware_manager.print_summary()
        except Exception as ex:
            print(f"[WARN] Failed to initialize HardwareManager: {ex}")

        # ZoneManager - inject zones list from merged config
        zones_config = self.data.get("zones", [])
        if zones_config:
            try:
                self.zone_manager = ZoneManager(zones_config)
                self.zone_manager.print_summary()
            except Exception as ex:
                print(f"[WARN] Failed to initialize ZoneManager: {ex}")
        else:
            print("[WARN] No zones defined in config!")

        # AnimationManager - inject merged config data (no file loading)
        try:
            self.animation_manager = AnimationManager(self.data)
            self.animation_manager.print_summary()
        except Exception as ex:
            print(f"[WARN] Failed to initialize AnimationManager: {ex}")

        # ColorManager - inject merged config data (no file loading)
        try:
            color_data = {
                'presets': self.data.get('presets', {}),
                'preset_order': self.data.get('preset_order', [])
            }
            self.color_manager = ColorManager(color_data)
        except Exception as ex:
            log("Failed to initialize ColorManager", LogLevel.WARN, error=str(ex))

        # ParameterManager - inject merged config data (no file loading)
        try:
            self.parameter_manager = ParameterManager(self.data)
            self.parameter_manager.print_summary()
        except Exception as ex:
            log("Failed to initialize ParameterManager", LogLevel.WARN, error=str(ex))

    # ===== Convenience Properties =====

    @property
    def zones(self) -> Dict[str, list]:
        """
        Get zones in old dict format for ZoneStrip compatibility

        Returns:
            Dict with zone tag as key and [start, end] as value
            Example: {"lamp": [0, 18], "top": [19, 22], ...}
        """
        if self.zone_manager:
            return self.zone_manager.get_zone_dict()
        return {}

    # ===== Zone Access API (delegation to ZoneManager) =====

    def get_zone(self, tag: str) -> Optional['Zone']:
        """
        Get zone object by tag

        Args:
            tag: Zone tag (e.g., "lamp", "top")

        Returns:
            Zone object or None if not found
        """
        if self.zone_manager:
            return self.zone_manager.get_zone(tag)
        return None

    def get_all_zones(self) -> List['Zone']:
        """
        Get all zone objects

        Returns:
            List of all Zone objects
        """
        if self.zone_manager:
            return self.zone_manager.zones
        return []

    def get_enabled_zones(self) -> List['Zone']:
        """
        Get only enabled zone objects

        Returns:
            List of enabled Zone objects
        """
        if self.zone_manager:
            return self.zone_manager.get_enabled_zones()
        return []

    def get_zone_tags(self) -> List[str]:
        """
        Get list of enabled zone tags in order

        Returns:
            List of zone tags: ["strip", "lamp", "left", "top", "right", "bottom"]
        """
        if self.zone_manager:
            return self.zone_manager.get_zone_tags()
        return []
