"""
Config Manager

Robust configuration loader and validator for LED control system.

- Loads user config from config/config.json
- Falls back to config/config_defaults.json if missing or invalid
- Provides safe access to hardware, zone, and default sections
"""

import json
import os


class ConfigManager:
    """
    Manages configuration loading and access.

    Args:
        path (str): Path to JSON configuration file.

    Attributes:
        data (dict): Raw configuration data.
    """
    
    
    def __init__(self,
                 config_path="config/config.json",
                 config_defaults_path="config/config_defaults.json"):
        self.config_path = config_path
        self.config_defaults_path = config_defaults_path
        self.data = self._load_config()
        
    def _load_config(self):
        """Load configuration file with full error handling."""
        config_data = self._try_load_file(self.config_path)

        if config_data:
            if self._validate_config(config_data):
                print(f"[CONFIG] Using user config: {self.config_path}")
                return config_data
            else:
                print(f"[CONFIG] Validation failed for {self.config_path}, using defaults.")

        print(f"[CONFIG] Loading fallback config: {self.config_defaults_path}")
        defaults_data = self._try_load_file(self.config_defaults_path)
        if not defaults_data:
            raise RuntimeError("[CONFIG] Unable to load default configuration file.")

        if not self._validate_config(defaults_data):
            raise RuntimeError("[CONFIG] Default configuration is invalid.")

        print("[CONFIG] Running on fallback (default) configuration.")
        return defaults_data
    
    def _try_load_file(self, path):
        """Attempt to read and parse a JSON config file."""
        if not os.path.exists(path):
            print(f"[CONFIG] File not found: {path}")
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError as e:
            print(f"[CONFIG] JSON parsing error in {path}: {e}")
        except IOError as e:
            print(f"[CONFIG] IO error reading {path}: {e}")
        except Exception as e:
            print(f"[CONFIG] Unexpected error reading {path}: {e}")
            traceback.print_exc()

        return None
    
    def _validate_config(self, cfg):
        """Check config structure and content validity."""
        try:
            # --- Hardware ---
            hw = cfg.get("hardware", {}).get("gpio", {})
            if not hw:
                print("[CONFIG] Missing section: hardware.gpio")
                return False

            required_keys = ["preview_panel", "led_strip", "encoders", "buttons"]
            for key in required_keys:
                if key not in hw:
                    print(f"[CONFIG] Missing GPIO key: {key}")
                    return False

            # --- Encoders ---
            enc = hw.get("encoders", {})
            for name in ["zone_selector", "modulator"]:
                if name not in enc:
                    print(f"[CONFIG] Missing encoder definition: {name}")
                    return False
                for pin in ["clk", "dt", "sw"]:
                    if pin not in enc[name]:
                        print(f"[CONFIG] Missing encoder pin: {name}.{pin}")
                        return False

            # --- Zones ---
            zones = cfg.get("zones")
            if not isinstance(zones, list) or not zones:
                print("[CONFIG] No zones defined.")
                return False

            seen = set()
            for z in zones:
                if "name" not in z or "length" not in z or "order" not in z:
                    print(f"[CONFIG] Incomplete zone definition: {z}")
                    return False
                if z["name"] in seen:
                    print(f"[CONFIG] Duplicate zone name: {z['name']}")
                    return False
                seen.add(z["name"])

            # --- Defaults ---
            defaults = cfg.get("defaults", {})
            for k in ["brightness", "mode", "color_mode"]:
                if k not in defaults:
                    print(f"[CONFIG] Missing defaults field: {k}")
                    return False

            return True

        except Exception as e:
            print(f"[CONFIG] Validation error: {e}")
            traceback.print_exc()
            return False
        
    # ===== Public properties =====

    @property
    def hardware_gpio(self):
        """Return GPIO configuration section."""
        return self.data.get("hardware", {}).get("gpio", {})

    @property
    def zones(self):
        """Return list of zones definitions."""
        return self.data.get("zones", [])

    @property
    def defaults(self):
        """Return default system settings."""
        return self.data.get("defaults", {})

    # ===== Utility =====

    def get_zone_by_name(self, name):
        """Get zone dictionary by name."""
        for zone in self.zones:
            if zone["name"] == name:
                return zone
        return None