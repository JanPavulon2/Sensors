"""
Dummy keyboard adapter for platforms without proper keyboard support (e.g., Windows).
Does nothing - just prevents crashes during initialization.
"""

import asyncio
from services.event_bus import EventBus
from .keyboard_adapter_interface import IKeyboardAdapter


class DummyKeyboardAdapter:
    """
    Dummy keyboard adapter that does nothing.

    Used on Windows or when no real keyboard adapter is available.
    Allows the application to start without crashing.
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def run(self) -> None:
        """
        Main loop that does nothing.
        Just yields to event loop indefinitely.
        """
        try:
            while True:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
