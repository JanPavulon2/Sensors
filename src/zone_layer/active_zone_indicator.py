from __future__ import annotations

import asyncio
import math
from typing import Optional

from models.enums import ZoneID, ZoneRenderMode, FramePriority, FrameSource
from models.color import Color
from models.frame_v2 import SingleZoneFrame
from engine.frame_manager import FrameManager

from lifecycle.task_registry import create_tracked_task, TaskCategory
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.GENERAL)


class ActiveZoneIndicator:
    """
    Visual indicator for the currently selected zone while edit mode is active.

    This class:
      - does NOT fetch zone state from services (no polling)
      - is fully driven by LightingController events
      - runs a single internal animation loop
      - pushes PULSE-priority frames into FrameManager
    """

    def __init__(self, frame_manager: FrameManager):
        self.frame_manager = frame_manager

        # runtime state
        self._edit_mode: bool = False
        self._active_zone: Optional[ZoneID] = None
        self._render_mode: Optional[ZoneRenderMode] = None

        # task state
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

        # animation params
        self._pulse_steps = 40
        self._pulse_cycle = 1.0  # seconds

    # ----------------------------------------------------------------------
    # Public API — called by LightingController
    # ----------------------------------------------------------------------

    def set_active_zone(self, zone_id: ZoneID) -> None:
        """Called when the user cycles zone selection."""
        self._active_zone = zone_id
        log.debug(f"[Indicator] active zone → {zone_id.name}")
        self._restart_if_needed()

    def set_render_mode(self, mode: ZoneRenderMode) -> None:
        """Called when zone's render mode changes (STATIC <-> ANIMATION)."""
        self._render_mode = mode
        log.debug(f"[Indicator] render mode → {mode.name}")
        self._restart_if_needed()

    def set_edit_mode(self, enabled: bool) -> None:
        """
        Called when edit mode toggles on/off.
        """
        log.info(f"[Indicator] edit mode → {enabled}")
        self._edit_mode = enabled

        if enabled:
            self._start()
        else:
            self._stop()

    # ----------------------------------------------------------------------
    # Internals — task management
    # ----------------------------------------------------------------------

    def _start(self) -> None:
        """Start the indicator loop."""
        if self._running:
            return

        if self._active_zone is None or self._render_mode is None:
            return  # cannot run without zone + mode

        log.info("[Indicator] starting")
        self._running = True
        self._task = create_tracked_task(
            self._loop(),
            category=TaskCategory.BACKGROUND,
            description="Active Zone Indicator Loop"
        )

    def _stop(self) -> None:
        """Stop the indicator loop synchronously."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        log.info("[Indicator] stopped")

    async def stop_async(self) -> None:
        """Stop the indicator loop asynchronously (for shutdown)."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        log.info("[Indicator] stopped async")

    def _restart_if_needed(self) -> None:
        """Restart loop only if edit mode is active."""
        if not self._edit_mode:
            return

        self._stop()
        self._start()

    # ----------------------------------------------------------------------
    # Main loop
    # ----------------------------------------------------------------------

    async def _loop(self) -> None:
        """
        Main animation loop.
        Chooses pattern based on render mode.
        """
        while self._running:
            if self._active_zone is None or self._render_mode is None:
                await asyncio.sleep(0.05)
                continue

            if self._render_mode == ZoneRenderMode.STATIC:
                await self._static_pulse(self._active_zone)

            elif self._render_mode == ZoneRenderMode.ANIMATION:
                await self._animation_highlight(self._active_zone)

            else:
                await asyncio.sleep(0.05)

    # ----------------------------------------------------------------------
    # STATIC → PULSE
    # ----------------------------------------------------------------------

    async def _static_pulse(self, zone_id: ZoneID) -> None:
        """
        Emits repeated pulses on the selected zone.
        """
        steps = self._pulse_steps
        cycle = self._pulse_cycle

        for step in range(steps):
            if not self._running or self._render_mode != ZoneRenderMode.STATIC:
                return

            # brightness scale 0.2 → 1.0
            scale = 0.2 + 0.8 * (math.sin(step / steps * 2 * math.pi - math.pi / 2) + 1) / 2

            color = Color.white().with_brightness(int(scale * 255))

            frame = SingleZoneFrame(
                zone_id=zone_id,
                color=color,
                priority=FramePriority.PULSE,
                source=FrameSource.PULSE,
                ttl=0.2,
            )

            await self.frame_manager.push_frame(frame)
            await asyncio.sleep(cycle / steps)

    # ----------------------------------------------------------------------
    # ANIMATION → HIGHLIGHT
    # ----------------------------------------------------------------------

    async def _animation_highlight(self, zone_id: ZoneID) -> None:
        """
        White halo flash to indicate active zone in animation mode.
        """
        if not self._running:
            return

        frame = SingleZoneFrame(
            zone_id=zone_id,
            color=Color.white(),
            priority=FramePriority.PULSE,
            source=FrameSource.PULSE,
            ttl=0.15
        )

        await self.frame_manager.push_frame(frame)
        await asyncio.sleep(0.15)
