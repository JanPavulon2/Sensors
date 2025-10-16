"""
ConfigManager - Configuration and State Management

Manages hardware configuration and runtime state for LED control system.

Architecture:
- config.yaml: Hardware GPIO mapping + zone defaults (READ-ONLY at runtime)
- config_backup.yaml: Automatic backup created on startup
- state.json: Runtime state (colors, brightness, modes) - auto-saved every 10s

The ConfigManager provides:
- Hardware configuration (GPIO pins, LED settings)
- Zone definitions (names, lengths, order)
- Runtime state management (current colors, brightness, modes)
- Auto-save functionality with configurable interval
- Backup/restore capabilities
"""

import yaml
import json
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from utils.colors import rgb_to_hue


class ConfigManager:
    """
    Manages configuration loading and runtime state persistence.

    Features:
    - Loads YAML hardware config (with validation)
    - Loads/saves JSON runtime state
    - Auto-backup config on startup
    - Auto-save state every N seconds
    - Thread-safe state updates

    Args:
        config_path (str): Path to YAML config file
        state_path (str): Path to JSON state file
        auto_save_interval (int): Auto-save interval in seconds (0 = disabled)

    Example:
        config = ConfigManager(auto_save_interval=10)

        # Get hardware config
        gpio = config.hardware_gpio
        zones = config.zones

        # Get/update runtime state
        hue = config.get_zone_state("lamp", "hue")
        config.update_zone_state("lamp", hue=180, brightness=128)

        # Manual save/load
        config.save_state()
        config.reload_state()
    """

    def __init__(self,
                 config_path="config/config.yaml",
                 state_path="config/state.json",
                 auto_save_interval=10):
        """
        Initialize ConfigManager with automatic config loading

        Args:
            config_path: Path to YAML config file
            state_path: Path to JSON state file
            auto_save_interval: Auto-save interval in seconds (0 to disable)
        """
        self.config_path = Path(config_path)
        self.state_path = Path(state_path)
        self.auto_save_interval = auto_save_interval

        # Loaded data
        self.config_data = {}
        self.state_data = {}

        # Thread-safety
        self.state_lock = threading.Lock()
        self.state_modified = False

        # Auto-save thread
        self.auto_save_thread = None
        self.auto_save_active = False

        # Load configuration
        self._load_config()
        self._backup_config()
        self._load_state()

        # Start auto-save if enabled
        if self.auto_save_interval > 0:
            self._start_auto_save()

    # =========================================================================
    # Config Loading (YAML - Hardware Configuration)
    # =========================================================================

    def _load_config(self):
        """Load YAML configuration file with validation"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r') as f:
                self.config_data = yaml.safe_load(f)

            if not self._validate_config(self.config_data):
                raise ValueError("Configuration validation failed")

            print(f"Loaded config: {self.config_path}")

        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error in {self.config_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading config: {e}")

    def _validate_config(self, cfg):
        """Validate configuration structure and required fields"""
        try:
            # Check top-level sections
            required_sections = ["hardware", "zones", "defaults"]
            for section in required_sections:
                if section not in cfg:
                    print(f"Missing section: {section}")
                    return False

            # Validate hardware.gpio
            hw = cfg.get("hardware", {}).get("gpio", {})
            if not hw:
                print("Missing hardware.gpio section")
                return False

            required_hw = ["preview_panel", "led_strip", "encoders", "buttons"]
            for key in required_hw:
                if key not in hw:
                    print(f"Missing hardware GPIO key: {key}")
                    return False

            # Validate encoders
            encoders = hw.get("encoders", {})
            for enc_name in ["zone_selector", "modulator"]:
                if enc_name not in encoders:
                    print(f"Missing encoder: {enc_name}")
                    return False
                for pin in ["clk", "dt", "sw"]:
                    if pin not in encoders[enc_name]:
                        print(f"Missing encoder pin: {enc_name}.{pin}")
                        return False

            # Validate zones
            zones = cfg.get("zones", [])
            if not isinstance(zones, list) or not zones:
                print("No zones defined")
                return False

            seen_tags = set()
            seen_orders = set()
            for z in zones:
                required_zone_fields = ["name", "tag", "length", "order", "enabled",
                                       "default_color", "default_brightness"]
                for field in required_zone_fields:
                    if field not in z:
                        print(f"Zone missing field '{field}': {z}")
                        return False

                # Check for duplicate tags
                if z["tag"] in seen_tags:
                    print(f"Duplicate zone tag: {z['tag']}")
                    return False
                seen_tags.add(z["tag"])

                # Check for duplicate orders
                if z["order"] in seen_orders:
                    print(f"Duplicate zone order: {z['order']}")
                    return False
                seen_orders.add(z["order"])

                # Validate color format [R, G, B]
                color = z.get("default_color", [])
                if not isinstance(color, list) or len(color) != 3:
                    print(f"Invalid color format for zone {z['tag']}: {color}")
                    return False

            # Validate defaults
            defaults = cfg.get("defaults", {})
            required_defaults = ["mode", "color_mode", "edit_mode", "lamp_solo"]
            for key in required_defaults:
                if key not in defaults:
                    print(f"Missing defaults field: {key}")
                    return False

            return True

        except Exception as e:
            print(f"Validation error: {e}")
            return False

    def _backup_config(self):
        """Create backup of config.yaml -> config_backup.yaml"""
        try:
            backup_path = self.config_path.parent / "config_backup.yaml"
            shutil.copy2(self.config_path, backup_path)
            print(f"Backup created: {backup_path}")
        except Exception as e:
            print(f"Warning: Failed to create backup: {e}")

    # =========================================================================
    # State Loading/Saving (JSON - Runtime State)
    # =========================================================================

    def _load_state(self):
        """Load JSON state file or create from defaults"""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r') as f:
                    self.state_data = json.load(f)
                print(f"Loaded state: {self.state_path}")
                return
            except json.JSONDecodeError as e:
                print(f"State file corrupted, creating from defaults: {e}")
            except Exception as e:
                print(f"Error loading state: {e}")

        # Create state from config defaults
        print("Creating new state from defaults...")
        self.state_data = self._create_default_state()
        self.save_state()

    def _create_default_state(self):
        """Create default state structure from config defaults"""
        defaults = self.config_data.get("defaults", {})
        zones_config = self.config_data.get("zones", [])

        # Build zones state dict
        zones_state = {}
        for zone in zones_config:
            tag = zone["tag"]
            r, g, b = zone["default_color"]
            hue = rgb_to_hue(r, g, b)

            zones_state[tag] = {
                "hue": hue,
                "preset_index": 0,
                "brightness": zone["default_brightness"],
                "enabled": zone["enabled"],
                "animation": None
            }

        return {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "system": {
                "power": True,
                "edit_mode": defaults.get("edit_mode", True),
                "lamp_solo": defaults.get("lamp_solo", False),
                "animation_running": False,
                "current_mode": defaults.get("mode", "COLOR_SELECT"),
                "color_mode": defaults.get("color_mode", "HUE"),
                "anim_param_mode": "SPEED",
                "preview_mode": "COLOR_DISPLAY",
                "selected_zone_index": 0,
                "selected_preset_index": 0,
                "selected_animation_index": 0
            },
            "zones": zones_state,
            "animation": {
                "current": "static",
                "speed": defaults.get("animation_speed", 50),
                "color1": [255, 0, 0],
                "color2": [0, 0, 255],
                "intensity": defaults.get("animation_intensity", 50)
            },
            "quick_action": {
                "lamp_saved_state": None
            }
        }

    def save_state(self):
        """Save current state to JSON file"""
        try:
            with self.state_lock:
                self.state_data["last_updated"] = datetime.now().isoformat()

                with open(self.state_path, 'w') as f:
                    json.dump(self.state_data, f, indent=2)

                self.state_modified = False

            print(f"State saved: {self.state_path}")

        except Exception as e:
            print(f"Error saving state: {e}")

    def reload_state(self):
        """Reload state from JSON file"""
        self._load_state()

    # =========================================================================
    # Auto-Save Thread
    # =========================================================================

    def _auto_save_loop(self):
        """Background thread that auto-saves state periodically"""
        while self.auto_save_active:
            time.sleep(self.auto_save_interval)

            with self.state_lock:
                if self.state_modified:
                    self.save_state()

    def _start_auto_save(self):
        """Start auto-save background thread"""
        if self.auto_save_thread and self.auto_save_thread.is_alive():
            return

        self.auto_save_active = True
        self.auto_save_thread = threading.Thread(
            target=self._auto_save_loop,
            daemon=True,
            name="ConfigAutoSave"
        )
        self.auto_save_thread.start()
        print(f"Auto-save enabled (every {self.auto_save_interval}s)")

    def stop_auto_save(self):
        """Stop auto-save thread and perform final save"""
        self.auto_save_active = False
        if self.auto_save_thread:
            self.auto_save_thread.join(timeout=2.0)

        # Final save
        if self.state_modified:
            self.save_state()

    # =========================================================================
    # Public Properties - Hardware Config (Read-Only)
    # =========================================================================

    @property
    def hardware_gpio(self):
        """Get hardware GPIO configuration"""
        return self.config_data.get("hardware", {}).get("gpio", {})

    @property
    def led_settings(self):
        """Get LED hardware settings"""
        return self.config_data.get("hardware", {}).get("led_settings", {})

    @property
    def zones(self):
        """Get list of zone configurations (sorted by order)"""
        zones = self.config_data.get("zones", [])
        return sorted(zones, key=lambda z: z["order"])

    @property
    def zone_tags(self):
        """Get list of zone tags in order"""
        return [z["tag"] for z in self.zones]

    @property
    def defaults(self):
        """Get system defaults"""
        return self.config_data.get("defaults", {})

    @property
    def color_presets(self):
        """Get color presets list"""
        return self.config_data.get("color_presets", [])

    def get_zone_config(self, zone_tag):
        """
        Get zone configuration by tag

        Args:
            zone_tag: Zone tag (e.g., "lamp", "top")

        Returns:
            Zone config dict or None if not found
        """
        for zone in self.zones:
            if zone["tag"] == zone_tag:
                return zone
        return None

    # =========================================================================
    # Public API - Runtime State (Read/Write)
    # =========================================================================

    def get_system_state(self, key=None):
        """
        Get system state value(s)

        Args:
            key: Specific key to get, or None for entire system state

        Returns:
            Value or dict
        """
        with self.state_lock:
            system = self.state_data.get("system", {})
            if key is None:
                return system.copy()
            return system.get(key)

    def update_system_state(self, **kwargs):
        """
        Update system state fields

        Args:
            **kwargs: Key-value pairs to update in system state

        Example:
            config.update_system_state(edit_mode=True, current_mode="BRIGHTNESS_ADJUST")
        """
        with self.state_lock:
            system = self.state_data.setdefault("system", {})
            system.update(kwargs)
            self.state_modified = True

    def get_zone_state(self, zone_tag, key=None):
        """
        Get zone runtime state

        Args:
            zone_tag: Zone tag (e.g., "lamp")
            key: Specific key to get, or None for entire zone state

        Returns:
            Value or dict
        """
        with self.state_lock:
            zones = self.state_data.get("zones", {})
            zone = zones.get(zone_tag, {})
            if key is None:
                return zone.copy()
            return zone.get(key)

    def update_zone_state(self, zone_tag, **kwargs):
        """
        Update zone runtime state

        Args:
            zone_tag: Zone tag (e.g., "lamp")
            **kwargs: Key-value pairs to update

        Example:
            config.update_zone_state("lamp", hue=180, brightness=255)
        """
        with self.state_lock:
            zones = self.state_data.setdefault("zones", {})
            zone = zones.setdefault(zone_tag, {})
            zone.update(kwargs)
            self.state_modified = True

    def get_animation_state(self, key=None):
        """Get animation state"""
        with self.state_lock:
            anim = self.state_data.get("animation", {})
            if key is None:
                return anim.copy()
            return anim.get(key)

    def update_animation_state(self, **kwargs):
        """Update animation state"""
        with self.state_lock:
            anim = self.state_data.setdefault("animation", {})
            anim.update(kwargs)
            self.state_modified = True

    def get_quick_action_state(self, key=None):
        """Get quick action state"""
        with self.state_lock:
            qa = self.state_data.get("quick_action", {})
            if key is None:
                return qa.copy()
            return qa.get(key)

    def update_quick_action_state(self, **kwargs):
        """Update quick action state"""
        with self.state_lock:
            qa = self.state_data.setdefault("quick_action", {})
            qa.update(kwargs)
            self.state_modified = True

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def reset_to_defaults(self):
        """Reset runtime state to defaults from config"""
        print("Resetting state to defaults...")
        with self.state_lock:
            self.state_data = self._create_default_state()
            self.state_modified = True
        self.save_state()

    def cleanup(self):
        """Cleanup resources (stop auto-save, final save)"""
        print("Cleaning up ConfigManager...")
        self.stop_auto_save()
