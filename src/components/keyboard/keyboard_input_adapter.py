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

log = get_logger().for_category(LogCategory.HARDWARE)

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

        Tries evdev first (with 1 second detection timeout), then falls
        back to stdin if no physical keyboard found.

        Blocks until cancelled (Ctrl+C or asyncio task cancellation).
        """
        log.info("Initializing keyboard input adapter")

        # Try evdev first (with short timeout to detect if keyboard exists)
        evdev_task = asyncio.create_task(self.evdev_adapter.run())

        try:
            # Wait 1 second for evdev to either:
            # 1. Return False immediately (no device found) → fallback to stdin
            # 2. Block on async_read_loop() (device found) → timeout, stay with evdev
            result = await asyncio.wait_for(evdev_task, timeout=1.0)

            # Evdev returned a result (didn't timeout)
            if not result:
                # Evdev returned False (no device found) - fallback to stdin
                log.info("No physical keyboard detected, using STDIN mode")
                # Await stdin_adapter and if it somehow completes,  stay in this loop forever
                while True:
                    try:
                        await self.stdin_adapter.run()
                    except asyncio.CancelledError:
                        raise  # Propagate cancellation up
                    except Exception as e:
                        log.warn(f"Stdin adapter error: {e}, retrying...")
                        await asyncio.sleep(0.1)
            else:
                # Evdev succeeded (shouldn't normally happen as it blocks indefinitely)
                log.info("Evdev keyboard active")
                return

        except asyncio.TimeoutError:
            # Timeout = evdev is blocking = keyboard device found and working!
            log.info("Physical keyboard active (evdev mode)")
            # Let evdev_task continue running until cancellation
            # This blocks indefinitely until task is cancelled
            await evdev_task

        except asyncio.CancelledError:
            # Cancellation during detection - clean up and propagate
            evdev_task.cancel()
            raise
