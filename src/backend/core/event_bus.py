

# =========================================================
# core/event_bus.py
# =========================================================

import asyncio
from uuid import UUID
from typing import Callable, Coroutine, List
from core.message import Message


class EventBus:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.subscribers: List[Callable] = []

    def subscribe(self, handler: Callable[[Message, UUID], Coroutine]):
        self.subscribers.append(handler)

    async def publish(self, message: Message, port_id: UUID):
        await self.queue.put((message, port_id))

    async def run(self):
        while True:
            msg, port_id = await self.queue.get()
            for sub in self.subscribers:
                await sub(msg, port_id)
