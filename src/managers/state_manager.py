import aiofiles
import json
from pathlib import Path
from copy import deepcopy

class StateManager:
    def __init__(self, path="config/state.json"):
        self.path = Path(path)
        self.state = {}

    async def load(self, defaults=None):
        """Load state asynchronously; fallback to defaults if missing."""
        try:
            async with aiofiles.open(self.path, "r", encoding="utf-8") as f:
                content = await f.read()
                self.state = json.loads(content)
        except Exception as ex:
            print(f"[WARN] Loading state.json failed: {ex}")
            self.state = deepcopy(defaults or {})
        return self.state

    async def save(self):
        """Asynchronously save state to JSON."""
        async with aiofiles.open(self.path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(self.state, indent=2))

    def update_from_led(self, led):
        """Update state snapshot from LEDController."""
        snapshot = led.get_status()
        self.state.update(snapshot)