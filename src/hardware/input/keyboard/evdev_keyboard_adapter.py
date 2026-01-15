
# components/keyboard_input_adapter.py
from typing import Optional, Dict, List
import asyncio
from evdev import InputDevice, list_devices, ecodes
from evdev import util as evdev_util
from models.events import KeyboardKeyPressEvent
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory
from .keyboard_adapter_interface import IKeyboardAdapter

log = get_logger().for_category(LogCategory.HARDWARE)

class EvdevKeyboardAdapter(IKeyboardAdapter):
    """
    Physical keyboard input via Linux evdev (/dev/input/event*)

    Robust implementation:
    - Uses blocking device.read() executed in executor (thread) to avoid EAGAIN races
    - Maps keycodes via ecodes.bytype
    - Tracks modifiers (CTRL/SHIFT/ALT)
    - Publishes KeyboardKeyPressEvent(normalized_key, modifiers) to EventBus
    """

    def __init__(self, event_bus: EventBus, device_path: Optional[str] = None):
        self.event_bus = event_bus
        self.device_path = device_path
        self.device: Optional[InputDevice] = None
        self._running = False

        # Track modifier key states
        self._modifiers: Dict[str, bool] = {
            "CTRL": False,
            "SHIFT": False,
            "ALT": False
        }

    async def _find_keyboard_device(self) -> Optional[str]:
        """
        Detect and select the correct keyboard input device.

        Returns:
            Path to the best /dev/input/eventX device for a real keyboard.
        """
        candidates = []

        for path in list_devices():
            try:
                device = InputDevice(path)
                name = device.name
                caps = device.capabilities()

                if ecodes.EV_KEY not in caps:
                    continue

                raw_keys = caps.get(ecodes.EV_KEY, [])
                key_codes = [code if isinstance(code, int) else code[0] for code in raw_keys]

                # Check for presence of actual alphanumeric keys
                has_letters = any(ecodes.KEY_A <= code <= ecodes.KEY_Z for code in key_codes)
                has_space = ecodes.KEY_SPACE in key_codes
                has_enter = ecodes.KEY_ENTER in key_codes

                if has_letters and has_space and has_enter:
                    candidates.append((path, name, len(key_codes)))

                log.debug(
                    f"Keyboard candidate",
                    name=name,
                    path=path,
                    has_letters=has_letters,
                    num_keys=len(key_codes)
                )

            except Exception as e:
                log.error(f"Cannot inspect {path}: {e}")
                continue

        if not candidates:
            log.warn("No valid keyboard input devices found.")
            return None

        # Sort by number of keys (more = likely full keyboard)
        candidates.sort(key=lambda x: -x[2])
        best_path, best_name, num_keys = candidates[0]

        log.info(
            "Selected keyboard device",
            name=best_name,
            path=best_path,
            total_keys=num_keys
        )

        return best_path

    async def run(self) -> bool:
        """Main async loop reading keyboard events with retry and resilience."""
        if not self.device_path:
            self.device_path = await self._find_keyboard_device()

        if not self.device_path:
            log.warn("No physical keyboard found via evdev")
            return False

        try:
            self.device = InputDevice(self.device_path)
            if self.device is None:
                log.error(f"Device not found in '{self.device_path}'")
                return False
            
            log.info("Listening for physical keyboard input",
                     device=self.device.name, path=self.device_path)
        except (OSError, PermissionError) as e:
            log.error(f"Cannot open keyboard device: {e}")
            return False

        loop = asyncio.get_running_loop()
        log.info("Physical keyboard active (evdev mode)")

        try:
            while True:
                try:
                    # Read blocking in executor
                    events = await loop.run_in_executor(None, self.device.read)
                    for event in events:
                        if event.type == ecodes.EV_KEY:
                            await self._handle_key_event(event)

                except OSError as e:
                    log.warn(f"Temporary read error: {e}")
                    await asyncio.sleep(0.1)
                    continue  # retry after short delay
                except Exception as e:
                    log.error(f"Unexpected error in keyboard loop: {e}")
                    await asyncio.sleep(0.1)
                    continue

        except asyncio.CancelledError:
            log.debug("Evdev keyboard cancelled (task stopped)")
            raise
        finally:
            try:
                if self.device:
                    self.device.close()
            except Exception:
                pass

        return True
    
    async def _handle_key_event(self, event) -> None:
        log.info(
            "Keyboard key event",
            LogCategory=LogCategory.EVENT
        )
        
        """Handle keyboard event from evdev"""
        if event.type != ecodes.EV_KEY:
            return

        # Map keycode to readable name
        try:
            key_name = ecodes.bytype[event.type][event.code]
        except KeyError:
            log.debug(f"Unknown key code: {event.code}")
            return

        pressed = event.value == 1
        released = event.value == 0

        # update modifier states
        self._update_modifier_state(key_name, pressed=pressed)

        # only publish on key down (ignore key up/repeat)
        if not pressed:
            return

        normalized = self._normalize_key_name(key_name)
        if not normalized:
            return

        modifiers = [k for k, v in self._modifiers.items() if v]
        log.info(
            "Keyboard key pressed",
            LogCategory=LogCategory.EVENT,
            key=normalized,
            modifiers=modifiers if modifiers else None
        )

        await self.event_bus.publish(
            KeyboardKeyPressEvent(normalized, modifiers)
        )
    
    def stop(self) -> None:
        """Signal loop to stop (useful if you call run() as a task)"""
        self._running = False

    def _update_modifier_state(self, key_name: str, pressed: bool) -> None:
        k = (key_name or "").upper()
        if "CTRL" in k:
            self._modifiers["CTRL"] = pressed
        elif "SHIFT" in k:
            self._modifiers["SHIFT"] = pressed
        elif "ALT" in k:
            self._modifiers["ALT"] = pressed

    def _normalize_key_name(self, key_name: str) -> str:
        """
        Normalize key names: drop KEY_ prefix and left/right qualifiers.
        Return empty string for modifier-only keys.
        """
        if not key_name:
            return ""
        nk = key_name.replace("KEY_", "")
        # don't publish pure modifiers
        pure_mods = {
            "LEFTCTRL", "RIGHTCTRL", "LEFTSHIFT", "RIGHTSHIFT",
            "LEFTALT", "RIGHTALT", "LEFTMETA", "RIGHTMETA"
        }
        if nk in pure_mods:
            return ""
        nk = nk.replace("LEFT", "").replace("RIGHT", "")
        return nk

