

# =========================================================
# core/event_bus.py
# =========================================================

import asyncio
from typing import Callable, Coroutine, List

from core.domain.port_ref import PortRef
from core.message import Message


class EventBus:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.subscribers: List[Callable] = []

    def subscribe(self, handler: Callable[[Message, PortRef], Coroutine]):
        self.subscribers.append(handler)

    async def publish(self, message: Message, port_ref: PortRef):
        await self.queue.put((message, port_ref))

    async def run(self):
        while True:
            msg, port_ref = await self.queue.get()
            for sub in self.subscribers:
                await sub(msg, port_ref)
