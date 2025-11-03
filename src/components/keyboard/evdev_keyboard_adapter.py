
# components/keyboard_input_adapter.py
from typing import Optional, Dict, List
import asyncio
from evdev import InputDevice, list_devices, ecodes
from evdev import util as evdev_util
from models.events import KeyboardKeyPressEvent
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory

log = get_logger()

class EvdevKeyboardAdapter:
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
                    LogCategory.HARDWARE,
                    f"Keyboard candidate",
                    name=name,
                    path=path,
                    has_letters=has_letters,
                    num_keys=len(key_codes)
                )

            except Exception as e:
                log.error(LogCategory.HARDWARE, f"Cannot inspect {path}: {e}")
                continue

        if not candidates:
            log.warn(LogCategory.HARDWARE, "No valid keyboard input devices found.")
            return None

        # Sort by number of keys (more = likely full keyboard)
        candidates.sort(key=lambda x: -x[2])
        best_path, best_name, num_keys = candidates[0]

        log.info(
            LogCategory.HARDWARE,
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
            log.warning(LogCategory.HARDWARE, "No physical keyboard found via evdev")
            return False

        try:
            self.device = InputDevice(self.device_path)
            log.info(LogCategory.HARDWARE, "Listening for physical keyboard input",
                     device=self.device.name, path=self.device_path)
        except (OSError, PermissionError) as e:
            log.error(LogCategory.HARDWARE, f"Cannot open keyboard device: {e}")
            return False

        loop = asyncio.get_running_loop()
        log.info(LogCategory.HARDWARE, "Physical keyboard active (evdev mode)")

        try:
            while True:
                try:
                    # Read blocking in executor
                    events = await loop.run_in_executor(None, self.device.read)
                    for event in events:
                        if event.type == ecodes.EV_KEY:
                            await self._handle_key_event(event)

                except OSError as e:
                    log.warn(LogCategory.HARDWARE, f"Temporary read error: {e}")
                    await asyncio.sleep(0.1)
                    continue  # retry after short delay
                except Exception as e:
                    log.error(LogCategory.HARDWARE, f"Unexpected error in keyboard loop: {e}")
                    await asyncio.sleep(0.1)
                    continue

        except asyncio.CancelledError:
            log.debug(LogCategory.HARDWARE, "Evdev keyboard cancelled (task stopped)")
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
            LogCategory.EVENT,
            "Keyboard key event"
        )
        
        """Handle keyboard event from evdev"""
        if event.type != ecodes.EV_KEY:
            return

        # Map keycode to readable name
        try:
            key_name = ecodes.bytype[event.type][event.code]
        except KeyError:
            log.debug(LogCategory.HARDWARE, f"Unknown key code: {event.code}")
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
            LogCategory.EVENT,
            "Keyboard key pressed",
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


# class EvdevKeyboardAdapter:
#     """
#     Physical keyboard input via Linux evdev (/dev/input/event*)

#     Features:
#     - Async-native event loop (non-blocking)
#     - Modifier key state tracking (Ctrl, Shift, Alt)
#     - Works in headless mode (no X11 required)
#     - Device auto-detection

#     Publishes KeyboardKeyPressEvent to EventBus on key press.
#     """

#     def __init__(self, event_bus: EventBus, device_path: Optional[str] = None):
#         """
#         Initialize evdev keyboard adapter

#         Args:
#             event_bus: EventBus for publishing keyboard events
#             device_path: Path to input device (e.g., /dev/input/event5)
#                         If None, will auto-detect first keyboard device
#         """
#         self.event_bus = event_bus
#         self.device_path = device_path
#         self.device: Optional[InputDevice] = None

#         # Track modifier key states (updated on KEY_DOWN/KEY_UP)
#         self._modifiers: Dict[str, bool] = {
#             'CTRL': False,
#             'SHIFT': False,
#             'ALT': False
#         }

#     async def _find_keyboard_device(self) -> Optional[str]:
#         """
#         Find first keyboard input device under /dev/input

#         Returns:
#             Device path (e.g., /dev/input/event5) or None if not found
#         """
#         candidates = []

#         for path in list_devices():
#             try:
#                 device = InputDevice(path)
#                 name = device.name.lower()
#                 caps = device.capabilities()

#                 # Check if device has keyboard capabilities
#                 if ecodes.EV_KEY in caps:
#                     # Filter for keyboard-like devices (exclude mice, touchpads)
#                     if 'keyboard' in name or 'keypad' in name:
#                         # Check if device has actual keyboard keys (not just media keys)
#                         key_codes = caps.get(ecodes.EV_KEY, [])

#                         # Check for presence of common letter keys (A-Z)
#                         has_letters = any(
#                             code in key_codes
#                             for code in [ecodes.KEY_A, ecodes.KEY_Z, ecodes.KEY_M, ecodes.KEY_SPACE]
#                         )

#                         log.debug(
#                             LogCategory.HARDWARE,
#                             f"Keyboard device found: {device.name} at {path}",
#                             has_letters=has_letters,
#                             num_keys=len(key_codes)
#                         )

#                         # Prioritize devices with actual letter keys
#                         candidates.append((path, device.name, has_letters, len(key_codes)))

#             except (OSError, PermissionError) as e:
#                 log.debug(LogCategory.HARDWARE, f"Cannot access device {path}: {e}")
#                 continue

#         if not candidates:
#             log.warn(LogCategory.HARDWARE, "No keyboard input device found under /dev/input/")
#             return None

#         # Sort by: has_letters (True first), then num_keys (more keys first)
#         candidates.sort(key=lambda x: (not x[2], -x[3]))

#         best_path, best_name, has_letters, num_keys = candidates[0]
#         log.info(
#             LogCategory.HARDWARE,
#             "Found physical keyboard device",
#             name=best_name,
#             path=best_path,
#             has_letters=has_letters,
#             total_keys=num_keys
#         )

#         # Log other candidates for debugging
#         if len(candidates) > 1:
#             log.debug(
#                 LogCategory.HARDWARE,
#                 f"Skipped {len(candidates)-1} other keyboard device(s): " +
#                 ", ".join(f"{c[1]} ({c[0]})" for c in candidates[1:])
#             )

#         return best_path

#     async def run(self) -> bool:
#         """
#         Main async event loop reading keyboard events from evdev device

#         Returns:
#             True if device was found and loop started, False otherwise

#         Note: This method blocks until device disconnects or error occurs
#         """
#         # Auto-detect device if not specified
#         if not self.device_path:
#             self.device_path = await self._find_keyboard_device()

#         if not self.device_path:
#             log.warning(
#                 LogCategory.HARDWARE,
#                 "No physical keyboard found via evdev"
#             )
#             return False

#         try:
#             self.device = InputDevice(self.device_path)
#             # Grab exclusive access to prevent other processes from reading events
#             # self.device.grab()
#         except (OSError, PermissionError) as e:
#             log.error(
#                 LogCategory.HARDWARE,
#                 f"Cannot open keyboard device: {e}",
#                 e #path=self.device_path
#             )
#             return False

#         log.info(LogCategory.HARDWARE, "Listening for physical keyboard input",
#                  device=self.device.name, path=self.device_path)

#         loop = asyncio.get_running_loop()

#         try:
#             async for event in self.device.async_read_loop():
#                 if event.type == ecodes.EV_KEY:
#                     await self._handle_key_event(event)
#                     # for event in events:
#                     #     if event.type == ecodes.EV_KEY:
#                     #         await self._handle_key_event(event)

#         except asyncio.CancelledError:
#             log.debug(LogCategory.HARDWARE, "Evdev keyboard cancelled")
#             raise  # Re-raise to propagate cancellation
#         except OSError as e:
#             log.error(LogCategory.HARDWARE, f"Keyboard device error: {e}", device=self.device_path)
#             return False
#         finally:
#             # Release exclusive access on exit
#             if self.device:
#                 try:
#                     self.device.ungrab()
#                 except Exception:
#                     pass

#         return True

#     def _read_events(self):
#         """Blocking read of single event from device (runs in executor)"""
#         try:
#             # read_one() blocks until one event is available
#             return self.device.read()
#             if event:
#                 return [event]
#             return []
#         except BlockingIOError:
#             # No events available (shouldn't happen with blocking mode)
#             return []
#         except Exception as e:
#             log.error(LogCategory.HARDWARE, f"Device read error: {e}", e)
#             return []

#     async def _handle_key_event(self, event) -> None:
#         """Handle keyboard event from evdev"""
#         if event.type != ecodes.EV_KEY:
#             return

#         # Map keycode to readable name
#         try:
#             key_name = ecodes.bytype[event.type][event.code]
#         except KeyError:
#             log.debug(LogCategory.HARDWARE, f"Unknown key code: {event.code}")
#             return

#         pressed = event.value == 1
#         released = event.value == 0

#         # update modifier states
#         self._update_modifier_state(key_name, pressed=pressed)

#         # only publish on key down (ignore key up/repeat)
#         if not pressed:
#             return

#         normalized = self._normalize_key_name(key_name)
#         if not normalized:
#             return

#         modifiers = [k for k, v in self._modifiers.items() if v]
#         log.info(
#             LogCategory.EVENT,
#             "Keyboard key pressed",
#             key=normalized,
#             modifiers=modifiers if modifiers else None
#         )

#         await self.event_bus.publish(
#             KeyboardKeyPressEvent(normalized, modifiers)
#         )
    
#     # async def _handle_key_event(self, event) -> None:
#     #     """
#     #     Handle keyboard event from evdev

#     #     Args:
#     #         event: evdev.InputEvent with type EV_KEY
#     #     """
#     #     """Handle keyboard event from evdev"""
#     #     if event.type != ecodes.EV_KEY:
#     #         return

#     #     try:
#     #         key_name = ecodes.KEY[event.code]
#     #     except KeyError:
#     #         return  # unknown key

#     #     # key press/release
#     #     pressed = event.value == 1
#     #     released = event.value == 0

#     #     # update modifier states
#     #     self._update_modifier_state(key_name, pressed=pressed)

#     #     # only publish on key down (ignore repeat/up)
#     #     if not pressed:
#     #         return

#     #     normalized = self._normalize_key_name(key_name)
#     #     if not normalized:
#     #         return

#     #     modifiers = [k for k, v in self._modifiers.items() if v]
#     #     log.info(LogCategory.EVENT, "Keyboard key pressed",
#     #             key=normalized, modifiers=modifiers if modifiers else None)

#     #     await self.event_bus.publish(
#     #         KeyboardKeyPressEvent(normalized, modifiers)
#     #     )
#         # key_event = categorize(event)
#         # key_name = key_event.keycode

#         # # Handle list of keycodes (some keys return multiple codes)
#         # if isinstance(key_name, list):
#         #     key_name = key_name[0]

#         # # Update modifier state on key down/up
#         # if key_event.keystate == key_event.key_down:
#         #     self._update_modifier_state(key_name, pressed=True)
#         # elif key_event.keystate == key_event.key_up:
#         #     self._update_modifier_state(key_name, pressed=False)

#         # # Only publish on key down (ignore key up and repeat)
#         # if key_event.keystate == key_event.key_down:
#         #     normalized = self._normalize_key_name(key_name)

#         #     # Skip standalone modifier key presses (only track state)
#         #     if not normalized:
#         #         return

#         #     # Build current modifier list
#         #     modifiers = [k for k, v in self._modifiers.items() if v]

#         #     log.debug(
#         #         LogCategory.EVENT,
#         #         "Keyboard key pressed",
#         #         key=normalized,
#         #         modifiers=modifiers if modifiers else None
#         #     )

#         #     # Publish event to EventBus
#         #     await self.event_bus.publish(
#         #         KeyboardKeyPressEvent(normalized, modifiers)
#         #     )

#     def _update_modifier_state(self, key_name: str, pressed: bool) -> None:
#         """
#         Track modifier key state (pressed/released)

#         Args:
#             key_name: evdev key code (e.g., "KEY_LEFTCTRL")
#             pressed: True if key down, False if key up
#         """
#         key_upper = key_name.upper()

#         if 'CTRL' in key_upper:
#             self._modifiers['CTRL'] = pressed
#         elif 'SHIFT' in key_upper:
#             self._modifiers['SHIFT'] = pressed
#         elif 'ALT' in key_upper:
#             self._modifiers['ALT'] = pressed

#     def _normalize_key_name(self, key_name: str) -> str:
#         """
#         Normalize evdev key name to standard format

#         Args:
#             key_name: evdev keycode (e.g., "KEY_RIGHT", "KEY_LEFTCTRL")

#         Returns:
#             Normalized key name (e.g., "RIGHT", "A") or empty string for
#             standalone modifiers

#         Examples:
#             KEY_RIGHT → RIGHT
#             KEY_A → A
#             KEY_LEFTCTRL → "" (modifier only, don't publish)
#             KEY_LEFTSHIFT → "" (modifier only, don't publish)
#         """
#         # Remove KEY_ prefix
#         normalized = key_name.replace("KEY_", "")

#         # Don't publish standalone modifier key presses
#         # (we track their state but don't generate events)
#         modifier_keys = [
#             'LEFTCTRL', 'RIGHTCTRL',
#             'LEFTSHIFT', 'RIGHTSHIFT',
#             'LEFTALT', 'RIGHTALT',
#             'LEFTMETA', 'RIGHTMETA'
#         ]
#         if normalized in modifier_keys:
#             return ""

#         # Normalize left/right variants (e.g., LEFTARROW → ARROW)
#         # Note: This only affects non-modifier keys
#         normalized = normalized.replace("LEFT", "").replace("RIGHT", "")

#         return normalized
