"""Frame streaming service for Socket.IO output."""

import asyncio
from collections import deque
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
    
    async def _loop(self):
        while self._running:
            if self._queue:
                frame = self._queue.pop()  # latest only    
                await self._sio.emit(
                    "output_frame",
                    self._serialize(frame), 
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

    def _serialize(self, frame: OutputFrame) -> dict:
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
        return {
            "t": frame.t,
            "zones": {
                zone_id.name: [list(c.to_rgb()) for c in pixels]
                for zone_id, pixels in frame.zones.items()
            }
        }
