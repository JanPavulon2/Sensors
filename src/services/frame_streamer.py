"""Frame streaming service for Socket.IO output."""

import asyncio
from collections import deque
from typing import Callable, Dict, List, Optional, Tuple

from socketio import AsyncServer

from models.domain.output_frame import OutputFrame
from utils.logger import get_logger
from models.enums import LogCategory

log = get_logger().for_category(LogCategory.FRAME_MANAGER)


class FrameStreamer:
    """
    Serializes and emits OutputFrame to Socket.IO clients.

    Single responsibility: serialize OutputFrame and emit to /frames namespace.
    No logic, no state, just serialization.

    Throttles emission to 30 fps (every other frame from 60 fps render).
    """

    def __init__(self, sio: AsyncServer, target_fps: int = 30):
        """
        Initialize frame streamer.

        Args:
            sio: Socket.IO AsyncServer instance
            target_fps: Target streaming FPS (default 30)
        """
        self._sio = sio
        # Remote (ESP32) fixtures are merged into the same output_frame rather
        # than pushed here directly: FrameManager owns the frame cadence and
        # this queue has maxlen=2, so a second producer would simply overwrite
        # its frames. See services/remote_fixture_animator.py.
        self._remote_pixel_provider: Optional[
            Callable[[], Dict[str, List[Tuple[int, int, int]]]]
        ] = None
        self._last_frame: Optional[OutputFrame] = None
        self.target_fps = target_fps
        self._interval = 1.0 / target_fps
        self._queue: deque[OutputFrame] = deque(maxlen=2)
        self._task: asyncio.Task | None = None
        self._running = False
        self._frame_counter = 0
        
        log.info(f"FrameStreamer streaming loop started @ {self.target_fps} FPS")

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
    
    def set_remote_pixel_provider(
        self, provider: Callable[[], Dict[str, List[Tuple[int, int, int]]]]
    ) -> None:
        """Register a source of remote-fixture pixels to merge into each frame."""
        self._remote_pixel_provider = provider

    async def _loop(self):
        while self._running:
            if self._queue:
                self._last_frame = self._queue.pop()  # latest only

            # Emitted even with an empty queue so remote fixtures keep
            # animating in the browser when FrameManager is idle (no local
            # zones, or nothing changing) - otherwise a remote breathe would
            # freeze on screen while the real LED carried on breathing.
            if self._last_frame is not None or self._remote_pixel_provider is not None:
                await self._sio.emit(
                    "output_frame",
                    self._serialize(self._last_frame),
                    namespace="/frames",
                )
            await asyncio.sleep(self._interval)
            
    def push(self, frame: OutputFrame) -> None:
        self._queue.append(frame)
        # OLD: asyncio.create_task(self.emit(frame))
        
    async def emit(self, frame: OutputFrame) -> None:
        """
        Emit OutputFrame to all clients on /frames namespace.

        Throttles emission based on target_fps. For 30 fps target with 60 fps
        render, emits every other frame.

        Args:
            frame: OutputFrame to emit
        """
        # Throttle to target FPS
        self._frame_counter += 1
        # if self._frame_counter % self._emit_interval != 0:
        #     return

        try:
            payload = self._serialize(frame)
            await self._sio.emit(
                event="output_frame",
                data=payload,
                namespace="/frames"
            )
            
            # log.debug(
            #     "Streaming frame",
            #     t=frame.t,
            #     zones=len(frame.zones)
            # )
        except Exception as e:
            log.error(f"Failed to emit output frame: {e}", exc_info=True)

    def _serialize(self, frame: Optional[OutputFrame]) -> dict:
        """
        Serialize OutputFrame to JSON-compatible dict.

        Args:
            frame: OutputFrame to serialize

        Returns:
            Dict with structure:
            {
                "t": float,
                "zones": {
                    "FLOOR": [[r,g,b], [r,g,b], ...],
                    "CIRCLE": [[r,g,b], ...],
                    ...
                }
            }
        """
        zones = {}
        if frame is not None:
            zones = {
                # Local zones key on ZoneID; remote fixtures key on their
                # instance id, which is already a string.
                (key.name if hasattr(key, "name") else str(key)): [
                    list(c.to_rgb()) for c in pixels
                ]
                for key, pixels in frame.zones.items()
            }

        if self._remote_pixel_provider is not None:
            for fixture_id, pixels in self._remote_pixel_provider().items():
                zones[fixture_id] = [list(pixel) for pixel in pixels]

        return {
            "t": frame.t if frame is not None else 0.0,
            "zones": zones,
        }
