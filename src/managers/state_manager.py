"""
State Manager

Handles async loading/saving of application state to JSON.
Uses new Color.to_dict/from_dict format for simplified state structure.
"""

import aiofiles
import json
from pathlib import Path
from copy import deepcopy


class StateManager:
    """
    Manages application state persistence

    New state format (using Color.to_dict()):
    {
        "mode": "STATIC",  # MainMode enum name
        "edit_mode": true,
        "lamp_white_mode": false,
        "current_zone": "lamp",
        "animation": {
            "enabled": false,
            "name": null,
            "params": {}
        },
        "zones": {
            "lamp": {
                "color": {"mode": "HUE", "hue": 120},  # Color.to_dict()
                "brightness": 80,  # 0-100%
                "reversed": false
            },
            ...
        }
    }
    """

    def __init__(self, path="config/state.json"):
        """
        Initialize StateManager

        Args:
            path: Path to state.json file (relative to src/ directory)
        """
        # Resolve path relative to src/ directory
        src_dir = Path(__file__).parent.parent
        self.path = src_dir / path
        self.state = {}

    async def load(self, defaults=None):
        """
        Load state asynchronously; fallback to defaults if missing

        Args:
            defaults: Default state dict to use if file doesn't exist

        Returns:
            Loaded or default state dict
        """
        try:
            async with aiofiles.open(self.path, "r", encoding="utf-8") as f:
                content = await f.read()
                self.state = json.loads(content)
        except FileNotFoundError:
            # First run - use defaults
            self.state = deepcopy(defaults or {})
        except Exception as ex:
            print(f"[WARN] Loading state.json failed: {ex}")
            self.state = deepcopy(defaults or {})
        return self.state

    async def save(self):
        """
        Asynchronously save state to JSON

        Writes with indentation for human readability.
        """
        async with aiofiles.open(self.path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(self.state, indent=2))

    def update_from_led(self, led):
        """
        Update state snapshot from LEDController

        Args:
            led: LEDController instance

        Note: LEDController.get_status() should return state dict
              with Color objects already serialized via Color.to_dict()
        """
        snapshot = led.get_status()
        self.state.update(snapshot)

    def get(self, key, default=None):
        """Get state value by key"""
        return self.state.get(key, default)

    def set(self, key, value):
        """Set state value by key"""
        self.state[key] = value
