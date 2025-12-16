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
from models.enums import ZoneID, LEDStripID
from models.domain.zone import ZoneConfig
from models.zone_mapping import ZoneHardwareMapping, ZoneMappingConfig
from utils.enum_helper import EnumHelper
from utils.serialization import Serializer

if TYPE_CHECKING:
    from managers.hardware_manager import HardwareManager
    from managers.animation_manager import AnimationManager
    from managers.color_manager import ColorManager

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

    def __init__(self, gpio_manager, config_path="config/config.yaml", defaults_path="config/factory_defaults.yaml"):
        """
        Initialize ConfigManager

        Args:
            gpio_manager: Singleton GPIOManager instance for hardware registration
            config_path: Path to main config.yaml (relative to src/)
            defaults_path: Path to factory defaults fallback
        """
        self.gpio_manager_singleton = gpio_manager
        self.config_path = Path(config_path)
        self.factory_defaults_path = Path(defaults_path)
        self.data = {}

        # Sub-managers (initialized in load() with guaranteed non-None values)
        # Type hints declare non-Optional - load() MUST initialize these
        self.hardware_manager: 'HardwareManager'
        self.animation_manager: 'AnimationManager'
        self.color_manager: 'ColorManager'
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

        # HardwareManager - always initialize (required)
        # Pass singleton gpio_manager for centralized GPIO registration
        self.hardware_manager = HardwareManager(self.data, self.gpio_manager_singleton)

        # Verify zones exist in config
        zones_config = self.data.get("zones", [])
        if not zones_config:
            log.warn("No zones defined in config!")
        else:
            log.info(f"Loaded {len(zones_config)} zone definitions from config")

        # AnimationManager - always initialize with fallback to empty
        try:
            self.animation_manager = AnimationManager(self.data)
            anims = self.animation_manager.get_all_animations()
            log.info(f"AnimationManager initialized with {len(anims)} animations")
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

        # Build zone-to-hardware mapping
        self.zone_mapping = self._parse_zone_mapping()

    # ===== Zone Mapping =====

    def _parse_zone_mapping(self) -> ZoneMappingConfig:
        """
        Parse zone-to-hardware mappings from zone_mapping.yaml

        Converts raw YAML data to typed ZoneMappingConfig with ZoneID and LEDStripID enums.
        Falls back to empty mapping if parsing fails.

        Returns:
            ZoneMappingConfig with all zone-to-hardware mappings
        """
        try:
            mappings_raw = self.data.get("hardware_mappings", [])
            if not mappings_raw:
                log.warn("No zone-to-hardware mappings found!")
                return ZoneMappingConfig(mappings=[])

            mappings = []
            for mapping_entry in mappings_raw:
                try:
                    hardware_id = LEDStripID[mapping_entry["hardware_id"]]
                    zone_ids = [
                        Serializer.str_to_enum(zone_str, ZoneID)
                        # EnumHelper.to_enum(ZoneID, zone_str)
                        for zone_str in mapping_entry.get("zones", [])
                    ]

                    mapping = ZoneHardwareMapping(
                        hardware_id=hardware_id,
                        zones=zone_ids
                    )
                    mappings.append(mapping)
                    log.info(f"Mapped hardware {hardware_id.name} → zones: {[z.name for z in zone_ids]}")
                except KeyError as e:
                    log.error(f"Invalid zone mapping entry: {mapping_entry}, error: {e}")
                    continue

            result = ZoneMappingConfig(mappings=mappings)
            log.info(f"Loaded {len(mappings)} zone-to-hardware mappings")
            return result

        except Exception as ex:
            log.error(f"Failed to parse zone mappings: {ex}")
            return ZoneMappingConfig(mappings=[])

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

        # =====================================================================
        # MULTI-GPIO ARCHITECTURE: Automatic GPIO Assignment
        # =====================================================================
        # This elegant design separates hardware from domain logic:
        #
        # 1. hardware.yaml defines physical LED strips:
        #    - GPIO pins (18, 19, etc.)
        #    - LED types and color orders (WS2811/BGR, WS2812/GRB)
        #    - Physical pixel counts
        #
        # 2. zone_mapping.yaml maps zones to hardware strips:
        #    - Explicit zone→hardware connections
        #    - Single source of truth for "which zones are where"
        #
        # 3. zones.yaml defines logical zones:
        #    - Zone names, pixel counts, animation parameters
        #    - NO GPIO definitions (auto-assigned here!)
        #
        # ConfigManager joins all three during initialization:
        # - Reads zone_mapping.yaml to build zone→GPIO mappings
        # - Assigns zone.config.gpio automatically
        # - Calculates pixel indices per-GPIO (each chain starts at 0)
        #
        # Benefits:
        # - Add GPIO pins without touching zones.yaml
        # - Change LED types without redefining zones
        # - Move zones between GPIO chains easily
        # - Clear separation of concerns
        # =====================================================================

        # Build GPIO-to-zones mapping from zone_mapping.yaml
        # Maps zone_id (enum) → gpio (int)
        gpio_mapping = {}  # zone_id (enum) → gpio (int)

        # Step 1: Read zone_mapping.yaml and lookup GPIO from hardware.yaml
        for mapping in self.zone_mapping.mappings:
            # Get hardware config (contains GPIO pin)
            hardware_cfg = self.hardware_manager.get_strip(mapping.hardware_id)
            gpio_pin = hardware_cfg.gpio

            # Map each zone to its GPIO pin
            for zone_id in mapping.zones:
                gpio_mapping[zone_id] = gpio_pin

        # Step 2: Build zone configs with auto-assigned GPIO
        # IMPORTANT: Pixel indices are calculated PER-GPIO
        # (each GPIO's zones start from index 0, not global index)
        prev_end_by_gpio = {}  # gpio -> last_end_index (tracks per-GPIO sequences)
        zone_configs = []

        for zone_dict in zones_raw:
            pixel_count = zone_dict.get("pixel_count", 0)
            zone_id = EnumHelper.to_enum(ZoneID, zone_dict.get("id", "UNKNOWN"))

            # Assign GPIO from mapping (defaults to 18 if not found)
            gpio_pin = gpio_mapping.get(zone_id, 18)

            # Calculate start/end indices for this GPIO's pixel sequence
            # Each GPIO has independent pixel indexing (GPIO 18 starts at 0, GPIO 19 starts at 0, etc.)
            # Example:
            #   GPIO 18: FLOOR[0-17], LEFT[18-21], TOP[22-24], ... (51 total)
            #   GPIO 19: PIXEL[0-29], PIXEL2[30-59], PREVIEW[60-67] (68 total)
            if gpio_pin not in prev_end_by_gpio:
                prev_end_by_gpio[gpio_pin] = -1  # Initialize for this GPIO

            start_index = prev_end_by_gpio[gpio_pin] + 1
            end_index = start_index + pixel_count - 1
            prev_end_by_gpio[gpio_pin] = end_index  # Track last index for this GPIO

            zone_config = ZoneConfig(
                id=zone_id,
                display_name=zone_dict.get("name", "Unknown"),
                pixel_count=pixel_count,
                enabled=zone_dict.get("enabled", True),  # Preserve actual enabled state
                reversed=zone_dict.get("reversed", False),
                order=zone_dict.get("order", 0),
                start_index=start_index,
                end_index=end_index,
                gpio=gpio_pin  # AUTO-ASSIGNED from zone_mapping.yaml!
            )
            zone_configs.append(zone_config)

        log.info(f"Built {len(zone_configs)} ZoneConfig objects (includes disabled zones)")
        return zone_configs
