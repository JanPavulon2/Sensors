import asyncio
import sys
import termios
import tty
from typing import Optional, List
from services.event_bus import EventBus
from models.events import KeyboardKeyPressEvent
from utils.logger import get_logger, LogCategory

log = get_logger()

class StdinKeyboardAdapter:
    """
    Terminal stdin keyboard input (SSH/VSCode/local terminal)

    Features:
    - Async-native (non-blocking)
    - Proper escape sequence handling (arrow keys)
    - Ctrl+Key detection via control codes
    - Works over SSH without X11

    Publishes KeyboardKeyPressEvent to EventBus on key press.

    Note: Terminal must be in raw/cbreak mode. Settings are restored on exit.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize stdin keyboard adapter

        Args:
            event_bus: EventBus for publishing keyboard events
        """
        self.event_bus = event_bus
        self._old_settings = None

    async def run(self) -> None:
        """
        Main async event loop reading from stdin

        Terminal is set to cbreak mode (character-at-a-time input).
        Original settings are restored when loop exits.

        Note: Requires 2x Ctrl+C to exit cleanly:
        - First Ctrl+C: Interrupts hardware_loop, triggers shutdown
        - Second Ctrl+C: Unblocks stdin.read() (which runs in executor thread)

        This is a limitation of blocking stdin.read() in executor.
        Use evdev mode (physical keyboard) for instant shutdown.
        """
        log.info(LogCategory.HARDWARE, "Using STDIN keyboard input (SSH/VSCode terminal)")

        loop = asyncio.get_running_loop()

        # Save terminal settings and set to cbreak mode
        self._old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

        try:
            while True:
                # Read one character (non-blocking via executor)
                # Note: This will block until char available, making cancellation require 2x Ctrl+C
                char = await loop.run_in_executor(None, sys.stdin.read, 1)

                if not char:
                    continue

                # Handle escape sequences (arrow keys, function keys, etc.)
                if char == '\x1b':  # ESC character
                    await self._handle_escape_sequence(loop)

                # Handle Ctrl+Key combinations (0x01-0x1a = Ctrl+A to Ctrl+Z)
                # EXCEPT: Enter (0x0a) and Tab (0x09) which are NOT Ctrl+J/Ctrl+I
                elif '\x01' <= char <= '\x1a':
                    # Special cases: Enter and Tab are their own keys
                    if char == '\n':  # 0x0a = newline (Enter key, NOT Ctrl+J)
                        await self._publish_key('ENTER')
                    elif char == '\t':  # 0x09 = tab (Tab key, NOT Ctrl+I)
                        await self._publish_key('TAB')
                    else:
                        # Real Ctrl+Key combination
                        key = chr(ord(char) + 96).upper()  # 0x01 → 'A'
                        await self._publish_key(key, modifiers=['CTRL'])

                # Handle carriage return (alternative Enter on some terminals)
                elif char == '\r':
                    await self._publish_key('ENTER')

                # Handle Backspace/Delete
                elif char == '\x7f':
                    await self._publish_key('BACKSPACE')

                # Handle Space
                elif char == ' ':
                    await self._publish_key('SPACE')

                # Regular printable characters
                # Detect Shift by checking if character is uppercase
                elif char.isprintable():
                    modifiers = []

                    # Shift detection: uppercase letters indicate Shift was pressed
                    # Note: This won't work with Caps Lock, but good enough for testing
                    if char.isupper():
                        modifiers.append('SHIFT')
                        await self._publish_key(char, modifiers)
                    elif char in '!@#$%^&*()_+{}|:"<>?':  # Shifted symbols
                        modifiers.append('SHIFT')
                        # Map shifted symbol back to base key
                        shift_map = {
                            '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
                            '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
                            '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
                            ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'
                        }
                        base_key = shift_map.get(char, char).upper()
                        await self._publish_key(base_key, modifiers)
                    else:
                        # Regular lowercase letter or unshifted symbol
                        await self._publish_key(char.upper())

        except asyncio.CancelledError:
            log.info(LogCategory.HARDWARE, "STDIN keyboard input cancelled - shutting down")
            raise  # Re-raise to propagate cancellation
        finally:
            # Restore terminal settings (always runs, even on cancellation)
            if self._old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
                log.debug(LogCategory.HARDWARE, "Terminal settings restored")

    async def _handle_escape_sequence(self, loop) -> None:
        """
        Handle escape sequences (arrow keys, function keys)

        Arrow keys send: ESC [ {A|B|C|D}
        Function keys send: ESC [ {1-9} ~

        Args:
            loop: asyncio event loop for executor
        """
        try:
            # Peek next character with timeout (50ms)
            # If timeout, it's a standalone ESC key
            next_char = await asyncio.wait_for(
                loop.run_in_executor(None, sys.stdin.read, 1),
                timeout=0.05
            )

            if next_char == '[':  # CSI sequence (arrow keys, etc.)
                direction = await asyncio.wait_for(
                    loop.run_in_executor(None, sys.stdin.read, 1),
                    timeout=0.05
                )

                # Map arrow key codes
                arrow_keys = {
                    'A': 'UP',
                    'B': 'DOWN',
                    'C': 'RIGHT',
                    'D': 'LEFT'
                }

                key = arrow_keys.get(direction)
                if key:
                    await self._publish_key(key)
                else:
                    log.debug(
                        LogCategory.EVENT,
                        f"Unknown CSI sequence: ESC[{direction}"
                    )
            else:
                # Standalone ESC or unknown sequence
                await self._publish_key('ESCAPE')

        except asyncio.TimeoutError:
            # Timeout on peek - standalone ESC key
            await self._publish_key('ESCAPE')

    async def _publish_key(self, key: str, modifiers: Optional[List[str]] = None) -> None:
        """
        Publish keyboard event to EventBus

        Args:
            key: Key name (e.g., "A", "ENTER", "UP")
            modifiers: List of modifier keys (e.g., ["CTRL", "SHIFT"])
        """
        log.debug(
            LogCategory.EVENT,
            "Keyboard key pressed",
            key=key,
            modifiers=modifiers if modifiers else None
        )

        await self.event_bus.publish(
            KeyboardKeyPressEvent(key, modifiers)
        )
