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

log = get_logger().for_category(LogCategory.CONFIG) 



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
                log.info("Using include-based configuration")
                self.data = self._load_with_includes(main_config['include'], src_dir / self.config_path.parent)
            else:
                # Monolithic config (backward compatibility)
                log.info("Using monolithic configuration")
                self.data = main_config

        except Exception as ex:
            log.error("Failed to load config.yaml", error=str(ex), error_type=type(ex).__name__)
            log.warn("Falling back to factory defaults")

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
                        log.info(f"Loaded {filename}", keys=str(list(file_data.keys())))
            except FileNotFoundError:
                log.error(f"File not found: {filename}")
                raise
            except Exception as ex:
                log.error(f"Error loading {filename}", error=str(ex))
                raise

        log.info("Config merge complete", total_keys=len(merged), keys=str(list(merged.keys())[:10]))
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
            log.warn("No zones defined in config!")
        else:
            log.info(f"Loaded {len(zones_config)} zone definitions from config")

        # AnimationManager - always initialize with fallback to empty
        try:
            self.animation_manager = AnimationManager(self.data)
            self.animation_manager.print_summary()
        except Exception as ex:
            log.error("Failed to initialize AnimationManager, using empty", error=str(ex))
            self.animation_manager = AnimationManager({})

        # ColorManager - always initialize with fallback to empty
        try:
            color_data = {
                'presets': self.data.get('presets', {}),
                'preset_order': self.data.get('preset_order', [])
            }
            self.color_manager = ColorManager(color_data)
        except Exception as ex:
            log.warn("Failed to initialize ColorManager, using empty", error=str(ex))
            self.color_manager = ColorManager({})

        # ParameterManager - always initialize with fallback to empty
        try:
            self.parameter_manager = ParameterManager(self.data)
            self.parameter_manager.print_summary()
        except Exception as ex:
            log.error("Failed to initialize ParameterManager, using empty", error=str(ex))
            self.parameter_manager = ParameterManager({})

    # ===== Zone Access API =====

    def get_all_zones(self) -> List[ZoneConfig]:
        """
        Get ALL zones (enabled + disabled) with calculated indices and GPIO assignments

        IMPORTANT: Disabled zones preserve their pixel indices to prevent physical LED shifting.
        Domain layer (ZoneCombined.get_rgb()) renders disabled zones as black (0,0,0).

        GPIO assignment:
        - Reads hardware.yaml led_strips configuration for GPIO-to-zones mapping
        - Each zone is assigned to its GPIO based on the mapping
        - Default GPIO: 18 (main zone strip)

        Returns:
            List of ZoneConfig objects (immutable, with indices and GPIO assignments calculated)
        """
        zones_raw = self.data.get("zones", [])
        if not zones_raw:
            log.warn("No zones found in config!")
            return []

        # Sort by order (ALL zones, not just enabled)
        zones_raw.sort(key=lambda z: z.get("order", 0))

        # Build GPIO-to-zones mapping from hardware.yaml
        gpio_mapping = {}  # zone_id_str -> gpio
        for strip_cfg in self.hardware_manager.get_gpio_to_zones_mapping():
            gpio_pin = strip_cfg.get("gpio", 18)
            zone_list = strip_cfg.get("zones", [])
            for zone_name in zone_list:
                gpio_mapping[zone_name.upper()] = gpio_pin

        # Build zone configs with GPIO assignment
        # Pixel indices are calculated per-GPIO (each GPIO's zones start from index 0)
        prev_end_by_gpio = {}  # gpio -> last_end_index
        zone_configs = []

        for zone_dict in zones_raw:
            pixel_count = zone_dict.get("pixel_count", 0)
            zone_id = EnumHelper.to_enum(ZoneID, zone_dict.get("id", "UNKNOWN"))
            zone_id_str = zone_dict.get("id", "UNKNOWN").upper()

            # Assign GPIO from hardware mapping, default to 18
            gpio_pin = gpio_mapping.get(zone_id_str, 18)

            # Calculate start/end indices for this GPIO's sequence
            if gpio_pin not in prev_end_by_gpio:
                prev_end_by_gpio[gpio_pin] = -1

            start_index = prev_end_by_gpio[gpio_pin] + 1
            end_index = start_index + pixel_count - 1
            prev_end_by_gpio[gpio_pin] = end_index

            zone_config = ZoneConfig(
                id=zone_id,
                display_name=zone_dict.get("name", "Unknown"),
                pixel_count=pixel_count,
                enabled=zone_dict.get("enabled", True),  # Preserve actual enabled state
                reversed=zone_dict.get("reversed", False),
                order=zone_dict.get("order", 0),
                start_index=start_index,
                end_index=end_index,
                gpio=gpio_pin  # Assign GPIO from hardware mapping
            )
            zone_configs.append(zone_config)

        log.info(f"Built {len(zone_configs)} ZoneConfig objects (includes disabled zones)")
        return zone_configs
