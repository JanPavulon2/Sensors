"""
Keyboard Input Adapter - Hardware abstraction layer for keyboard input

Dual backend implementation:
- EvdevKeyboardAdapter: Physical keyboard via /dev/input (Linux evdev)
- StdinKeyboardAdapter: Terminal input for SSH/remote sessions

Publishes KeyboardKeyPressEvent to EventBus with proper modifier tracking.

Architecture note: This is a Layer 1 (HAL) component that publishes events
directly to EventBus, similar to ControlPanel. It does NOT extend ControlPanel
as that represents fixed physical hardware.
"""

import asyncio
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory
from .evdev_keyboard_adapter import EvdevKeyboardAdapter
from .stdin_keyboard_adapter import StdinKeyboardAdapter
log = get_logger()

class KeyboardInputAdapter:
    """
    Unified keyboard input adapter with automatic backend selection

    Strategy:
    1. Try evdev (physical keyboard) with timeout
    2. Fallback to stdin if evdev fails or times out

    This allows development/testing over SSH while supporting physical
    keyboards in production.

    Usage:
        adapter = KeyboardInputAdapter(event_bus)
        await adapter.run()  # Blocks until cancelled
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize keyboard input adapter

        Args:
            event_bus: EventBus for publishing keyboard events
        """
        self.event_bus = event_bus
        self.evdev_adapter = EvdevKeyboardAdapter(event_bus)
        self.stdin_adapter = StdinKeyboardAdapter(event_bus)

    async def run(self) -> None:
        """
        Run keyboard input adapter with automatic backend selection

        Tries evdev first (with 2 second detection timeout), then falls
        back to stdin if no physical keyboard found.

        Blocks until cancelled (Ctrl+C or asyncio task cancellation).
        """
        log.info(LogCategory.HARDWARE, "Initializing keyboard input adapter")

        # Try evdev first (with short timeout to detect if keyboard exists)
        evdev_task = asyncio.create_task(self.evdev_adapter.run())

        try:
            # Wait 1 second for evdev to either:
            # 1. Return False immediately (no device found) → fallback to stdin
            # 2. Block on async_read_loop() (device found) → timeout, continue with evdev
            result = await asyncio.wait_for(evdev_task, timeout=1.0)

            if not result:
                # Evdev returned False (no device found) - fallback to stdin
                log.info(LogCategory.HARDWARE, "No physical keyboard detected, using STDIN mode")
            else:
                # This shouldn't happen (evdev blocks indefinitely if device found)
                return

        except asyncio.TimeoutError:
            # Timeout = evdev is blocking = keyboard device found and working!
            log.info(LogCategory.HARDWARE, "Physical keyboard active (evdev mode)")
            # Let evdev_task continue running until cancellation
            await evdev_task
            return

        except asyncio.CancelledError:
            # Cancellation during detection - clean up and propagate
            evdev_task.cancel()
            raise

        # Fallback to stdin if evdev not available
        log.info(LogCategory.HARDWARE, "Starting STDIN keyboard input mode")
        await self.stdin_adapter.run()
