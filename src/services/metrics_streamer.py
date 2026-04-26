"""
MetricsStreamer — Periodically aggregates render metrics and streams to Socket.IO.

Lifecycle:
  - Auto-starts when the first /metrics Socket.IO client connects
  - Auto-stops when the last /metrics client disconnects
  - No background task runs when no clients are listening

Data flow:
  RenderMetricsCollector (ring buffers) → MetricsStreamer (1 Hz) → Socket.IO /metrics namespace
"""

from __future__ import annotations

import asyncio
from typing import Optional, TYPE_CHECKING

from utils.logger import get_logger
from models.enums import LogCategory

if TYPE_CHECKING:
    from socketio import AsyncServer
    from engine.render_metrics import RenderMetricsCollector

log = get_logger().for_category(LogCategory.FRAME_MANAGER)


class MetricsStreamer:
    """
    Periodically reads from RenderMetricsCollector and emits snapshots
    to connected /metrics Socket.IO clients.

    Only active when at least one metrics client is connected.
    Configurable emission interval (default 1 Hz).
    """

    def __init__(
        self,
        socketio_server: "AsyncServer",
        collector: "RenderMetricsCollector",
        interval: float = 1.0,
    ) -> None:
        self._socketio_server = socketio_server
        self._collector = collector
        self._interval = interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._client_count = 0

    @property
    def collector(self) -> "RenderMetricsCollector":
        return self._collector

    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, value: float) -> None:
        self._interval = max(0.25, min(5.0, value))

    async def start(self) -> None:
        """Start the metrics streaming loop."""
        if self._running:
            return
        self._running = True
        self._collector.enabled = True
        self._task = asyncio.create_task(self._streaming_loop())
        log.info("MetricsStreamer started", interval=self._interval)

    async def stop(self) -> None:
        """Stop the metrics streaming loop."""
        self._running = False
        self._collector.enabled = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        log.info("MetricsStreamer stopped")

    def on_client_connect(self) -> None:
        """Called when a /metrics Socket.IO client connects."""
        self._client_count += 1
        if self._client_count == 1 and not self._running:
            asyncio.create_task(self.start())

    def on_client_disconnect(self) -> None:
        """Called when a /metrics Socket.IO client disconnects."""
        self._client_count = max(0, self._client_count - 1)
        if self._client_count == 0 and self._running:
            asyncio.create_task(self.stop())

    async def _streaming_loop(self) -> None:
        """Emit metrics snapshot at configured interval."""
        while self._running:
            try:
                snapshot = self._collector.get_snapshot()
                await self._socketio_server.emit(
                    "metrics:snapshot",
                    snapshot,
                    namespace="/metrics",
                )
            except Exception as error:
                log.error(f"MetricsStreamer emit error: {error}")
            await asyncio.sleep(self._interval)
