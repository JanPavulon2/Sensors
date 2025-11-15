"""
Config Manager

Main configuration manager with include system support.
Loads modular YAML files and initializes sub-managers.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, TYPE_CHECKING
from utils.logger import get_logger, get_category_logger, LogLevel, LogCategory
from models.enums import ZoneID
from models.domain.zone import ZoneConfig
from utils.enum_helper import EnumHelper

if TYPE_CHECKING:
    from managers.hardware_manager import HardwareManager
    from managers.animation_manager import AnimationManager
    from managers.color_manager import ColorManager
    from managers.parameter_manager import ParameterManager

log = get_category_logger(LogCategory.CONFIG)



class ConfigManager:
    """
    Main configuration manager with include system support

    Loads config.yaml and processes include: directive to load modular YAML files.
    Initializes sub-managers (HardwareManager, AnimationManager, ColorManager, ParameterManager).
    Provides zone configuration via get_enabled_zones() method.

    Example:
        config = ConfigManager()
        config.load()

        # Access via properties
        hw_dict = config.hardware  # Returns dict
        zones = config.get_enabled_zones()  # Returns List[ZoneConfig] with calculated indices

        # Access via sub-managers
        enc_cfg = config.hardware_manager.get_encoder("zone_selector")
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

        # Sub-managers (initialized in load() with guaranteed non-None values)
        # Type hints declare non-Optional - load() MUST initialize these
        self.hardware_manager: 'HardwareManager'
        self.animation_manager: 'AnimationManager'
        self.color_manager: 'ColorManager'
        self.parameter_manager: 'ParameterManager'

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
        - AnimationManager: Animation metadata and parameters
        - ColorManager: Color preset definitions
        - ParameterManager: Parameter definitions and validation

        Note: Zone config is accessed directly via get_zones_config()
        """
        from managers.hardware_manager import HardwareManager
        from managers.animation_manager import AnimationManager
        from managers.color_manager import ColorManager
        from managers.parameter_manager import ParameterManager

        # HardwareManager - always initialize (required)
        self.hardware_manager = HardwareManager()
        self.hardware_manager.data = self.data
        self.hardware_manager.print_summary()

        # Verify zones exist in config
        zones_config = self.data.get("zones", [])
        if not zones_config:
            log("No zones defined in config!", LogLevel.WARN)
        else:
            log(f"Loaded {len(zones_config)} zone definitions from config")

        # AnimationManager - always initialize with fallback to empty
        try:
            self.animation_manager = AnimationManager(self.data)
            self.animation_manager.print_summary()
        except Exception as ex:
            log("Failed to initialize AnimationManager, using empty", LogLevel.WARN, error=str(ex))
            self.animation_manager = AnimationManager({})

        # ColorManager - always initialize with fallback to empty
        try:
            color_data = {
                'presets': self.data.get('presets', {}),
                'preset_order': self.data.get('preset_order', [])
            }
            self.color_manager = ColorManager(color_data)
        except Exception as ex:
            log("Failed to initialize ColorManager, using empty", LogLevel.WARN, error=str(ex))
            self.color_manager = ColorManager({})

        # ParameterManager - always initialize with fallback to empty
        try:
            self.parameter_manager = ParameterManager(self.data)
            self.parameter_manager.print_summary()
        except Exception as ex:
            log("Failed to initialize ParameterManager, using empty", LogLevel.WARN, error=str(ex))
            self.parameter_manager = ParameterManager({})

    # ===== Zone Access API =====

    def get_all_zones(self) -> List[ZoneConfig]:
        """
        Get ALL zones (enabled + disabled) with calculated indices

        IMPORTANT: Disabled zones preserve their pixel indices to prevent physical LED shifting.
        Domain layer (ZoneCombined.get_rgb()) renders disabled zones as black (0,0,0).

        Returns:
            List of ZoneConfig objects (immutable, with indices calculated)
        """
        zones_raw = self.data.get("zones", [])
        if not zones_raw:
            log("No zones found in config!", LogLevel.WARN)
            return []

        # Sort by order (ALL zones, not just enabled)
        zones_raw.sort(key=lambda z: z.get("order", 0))

        # Calculate indices for ALL zones (disabled zones preserve their pixel space)
        prev_end = -1
        zone_configs = []

        for zone_dict in zones_raw:
            pixel_count = zone_dict.get("pixel_count", 0)
            start_index = prev_end + 1
            end_index = start_index + pixel_count - 1
            prev_end = end_index

            # Build ZoneConfig object (preserve enabled flag)
            zone_id = EnumHelper.to_enum(ZoneID, zone_dict.get("id", "UNKNOWN"))
            zone_config = ZoneConfig(
                id=zone_id,
                display_name=zone_dict.get("name", "Unknown"),
                pixel_count=pixel_count,
                enabled=zone_dict.get("enabled", True),  # Preserve actual enabled state
                reversed=zone_dict.get("reversed", False),
                order=zone_dict.get("order", 0),
                start_index=start_index,
                end_index=end_index
            )
            zone_configs.append(zone_config)

        log(f"Built {len(zone_configs)} ZoneConfig objects (includes disabled zones)")
        return zone_configs
