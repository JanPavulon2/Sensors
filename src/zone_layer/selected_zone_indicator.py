from __future__ import annotations

import asyncio
import math
from typing import Optional

from models.enums import ZoneID, ZoneRenderMode, FramePriority, FrameSource
from models.color import Color
from models.frame import SingleZoneFrame
from engine.frame_manager import FrameManager
from lifecycle.task_registry import create_tracked_task, TaskCategory
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.INDICATOR)


class SelectedZoneIndicator:
    """
    Visual indicator for the currently selected zone while edit mode is active.

    
    Design:
    - event-driven (no services, no polling)
    - reacts to explicit notifications from LightingController
    """

    
    # ------------------------------------------------------------------
    # Tunable parameters (playground-friendly)
    # ------------------------------------------------------------------

    STATIC_PULSE_CYCLE_S = 0.5          # full pulse cycle duration
    STATIC_PULSE_STEPS = 48
    STATIC_MIN_SCALE = 0.15             # how dark pulse goes
    STATIC_MAX_SCALE = 2.60             # how bright pulse goes
    STATIC_TTL = 0.18

    ANIMATION_BLINK_TTL = 0.15
    ANIMATION_BLINK_INTERVAL = 0.35
    ANIMATION_HIGHLIGHT_COLOR = Color.white()

    OFF_ZONE_COLOR = Color.blue()
    OFF_ZONE_TTL = 0.25
    
    def __init__(self, frame_manager: FrameManager):
        self.frame_manager = frame_manager

        # ---- context (pushed from controller) ----
        self._edit_mode: bool = False
        self._selected_zone_id: Optional[ZoneID] = None
        self._render_mode: Optional[ZoneRenderMode] = None
        self._zone_is_on: bool = True
        self._zone_color: Optional[Color] = None
        self._zone_brightness: int = 100  # 0–100

        
        # ---- task state ----
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Context update API (called by LightingController)
    # ------------------------------------------------------------------

    def on_selected_zone_changed(self, zone_id: ZoneID) -> None:
        self._selected_zone_id = zone_id
        log.debug(f"On selected zone → {zone_id.name}")
        self._restart_if_active()

    def on_zone_render_mode_changed(self, mode: ZoneRenderMode) -> None:
        self._render_mode = mode
        log.debug(f"On render mode changed → {mode.name}")
        self._restart_if_active()

    def on_zone_color_changed(self, color: Color) -> None:
        self._zone_color = color
        log.debug(f"On zone color changed → {color}")

    def on_zone_is_on_changed(self, is_on: bool) -> None:
        self._zone_is_on = is_on
        log.info(f"On zone is on changed -> {is_on}")
        self._restart_if_active()

    def on_edit_mode_changed(self, enabled: bool) -> None:
        self._edit_mode = enabled
        log.info(f"On edit mode → {enabled}")

        if enabled:
            self._start()
        else:
            self._stop()
   
    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def _start(self) -> None:
        if self._running:
            return

        if not self._can_run():
            log.info("Indicator cant run")
            return

        log.info("Indicator starting")
        self._running = True
        self._task = create_tracked_task(
            self._loop(),
            category=TaskCategory.RENDER,
            description="Selected Zone Indicator"
        )

    def _stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        log.info("Indicator stopped")

    async def stop_async(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def _restart_if_active(self) -> None:
        if not self._edit_mode:
            return
        self._stop()
        self._start()

    def _can_run(self) -> bool:
        return (
            self._edit_mode
            and self._selected_zone_id is not None
            and self._render_mode is not None
        )
    

    # ------------------------------------------------------------------
    # Main render loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        while self._running:
            if not self._can_run():
                await asyncio.sleep(0.05)
                continue

            if not self._zone_is_on:
                await self._render_off_zone()
            elif self._render_mode == ZoneRenderMode.STATIC:
                await self._render_static_pulse()
            elif self._render_mode == ZoneRenderMode.ANIMATION:
                await self._render_animation_blink()
            else:
                await asyncio.sleep(0.1)

    # -----------------------------------
    # Render implementations
    # -----------------------------------
    
    async def _render_static_pulse(self) -> None:
        base_color = self._zone_color or Color.white()

        steps = self.STATIC_PULSE_STEPS
        cycle = self.STATIC_PULSE_CYCLE_S

        for step in range(steps):
            if not self._running or self._render_mode != ZoneRenderMode.STATIC:
                return

            phase = step / steps * 2 * math.pi - math.pi / 2
            scale = (
                self.STATIC_MIN_SCALE
                + (self.STATIC_MAX_SCALE - self.STATIC_MIN_SCALE)
                * (math.sin(phase) + 1) / 2
            )

            brightness_pct = max(0, min(100, int(scale * 100)))
            color = base_color.with_brightness(brightness_pct)
        
            frame = SingleZoneFrame(
                zone_id=self._selected_zone_id,
                color=color,
                priority=FramePriority.PULSE,
                source=FrameSource.PULSE,
                ttl=self.STATIC_TTL,
            )

            await self.frame_manager.push_frame(frame)
            await asyncio.sleep(cycle / steps)

    async def _render_animation_blink(self) -> None:
        frame = SingleZoneFrame(
            zone_id=self._selected_zone_id,
            color=self.ANIMATION_HIGHLIGHT_COLOR,
            priority=FramePriority.PULSE,
            source=FrameSource.PULSE,
            ttl=self.ANIMATION_BLINK_TTL,
        )

        await self.frame_manager.push_frame(frame)
        await asyncio.sleep(self.ANIMATION_BLINK_INTERVAL)

    async def _render_off_zone(self) -> None:
        frame = SingleZoneFrame(
            zone_id=self._selected_zone_id,
            color=self.OFF_ZONE_COLOR,
            priority=FramePriority.PULSE,
            source=FrameSource.PULSE,
            ttl=self.OFF_ZONE_TTL,
        )

        await self.frame_manager.push_frame(frame)
        await asyncio.sleep(self.OFF_ZONE_TTL)