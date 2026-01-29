import asyncio
import sys
import select
import termios
import tty
from typing import Optional, List
from services.event_bus import EventBus
from models.events import KeyboardKeyPressEvent
from utils.logger import get_logger, LogCategory
from .base import IKeyboardAdapter

log = get_logger().for_category(LogCategory.HARDWARE)

class StdinKeyboardAdapter(IKeyboardAdapter):
    """
    Terminal standard keyboard adapter

    Intended for:
    - SSH sessions
    - VS Code integrated terminal
    - Local Unix terminals
    
    Features:
    - Async-friendly (select + asyncio)
    - Escape sequence handling (arrow keys)
    - Ctrl+Key detection
    - Proper terminal mode handling (cbreak)
    
    Publishes KeyboardKeyPressEvent to EventBus on key press.

    Note: Terminal must be in raw/cbreak mode. Settings are restored on exit.
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._old_settings = None
        self._buffer = ""
        
    async def run(self) -> None:
        """
        Main async event loop reading from stdin (non-blocking with select.select())

        This method:
        - blocks until cancelled
        - raises RuntimeError if STDIN cannot be used as a keyboard
        """
        
        log.info("Starting STDIN keyboard adapter")

        # STDIN must be a TTY (SSH, local terminal, etc.)
        if not sys.stdin.isatty():
            log.info("STDIN is not a TTY, cannot use stdin keyboard adapter")
            raise RuntimeError("STDIN is not a TTY")
        
        # Save current terminal settings and switch to cbreak mode
        self._old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

        log.info("STDIN keyboard adapter active (cbreak mode enabled)")
        
        try:
            while True:
                # Non-blocking wait for input
                ready, _, _ = select.select([sys.stdin], [], [], 0.01)

                if not ready:
                    # Yield control to event loop
                    await asyncio.sleep(0)
                    continue

                # Data is available - read one character
                try:
                    char = sys.stdin.read(1)
                except (IOError, OSError) as e:
                    log.info("STDIN read error, stopping adapter", reason=str(e))
                    raise RuntimeError("STDIN read failed") from e

                if not char:
                    continue
                
                self._buffer += char
                await self._process_buffer()
                
                
        except asyncio.CancelledError:
            log.info("STDIN keyboard adapter cancelled")
            raise  
        
        finally:
            # Restore terminal settings (always runs, even on cancellation)
            if self._old_settings:
                termios.tcsetattr(
                    sys.stdin, 
                    termios.TCSADRAIN, 
                    self._old_settings
                )
                log.debug("Terminal settings restored")

    async def _process_buffer(self) -> None:
        """
        Consume buffered stdin input and emit keyboard events.

        IMPORTANT:
        - Process buffer in a loop
        - Emit events as soon as a full token is available
        """

        while self._buffer:
            # ------------------------------------------------------------
            # Arrow keys: ESC [ A/B/C/D
            # ------------------------------------------------------------
            if self._buffer.startswith('\x1b['):
                if len(self._buffer) < 3:
                    return  # wait for full sequence

                seq = self._buffer[:3]
                self._buffer = self._buffer[3:]

                arrow_map = {
                    '\x1b[A': 'UP',
                    '\x1b[B': 'DOWN',
                    '\x1b[C': 'RIGHT',
                    '\x1b[D': 'LEFT',
                }

                key = arrow_map.get(seq)
                if key:
                    log.info("Keyboard key pressed (stdin)", key=key)
                    await self._publish_key(key)
                else:
                    log.debug("Unknown escape sequence", sequence=repr(seq))

                continue  # <<< CRITICAL


            # ------------------------------------------------------------
            # Standalone ESC (only if nothing else follows)
            # ------------------------------------------------------------
            if self._buffer == '\x1b':
                return  # wait one tick for possible continuation

            if self._buffer.startswith('\x1b'):
                self._buffer = self._buffer[1:]
                await self._publish_key("ESCAPE")
                continue


            # ------------------------------------------------------------
            # Normal single-character handling
            # ------------------------------------------------------------
            char = self._buffer[0]
            self._buffer = self._buffer[1:]

            if char in ('\r', '\n'):
                await self._publish_key("ENTER")
            elif char == '\t':
                await self._publish_key("TAB")
            elif char == '\x7f':
                await self._publish_key("BACKSPACE")
            elif char == ' ':
                await self._publish_key("SPACE")
            elif '\x01' <= char <= '\x1a':
                key = chr(ord(char) + 96).upper()
                await self._publish_key(key, modifiers=["CTRL"])
            elif char.isprintable():
                if char.isupper():
                    await self._publish_key(char, modifiers=["SHIFT"])
                else:
                    await self._publish_key(char.upper())
                    
    async def _publish_key(self, key: str, modifiers: Optional[List[str]] = None) -> None:
        log.info(
            f"Keyboard key pressed (stdin): {key}",
            modifiers=modifiers if modifiers else None
        )

        await self.event_bus.publish(
            KeyboardKeyPressEvent(key, modifiers)
        )
        