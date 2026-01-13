from __future__ import annotations

import asyncio
import math
from typing import Optional

from models.enums import ZoneID, ZoneRenderMode, FramePriority, FrameSource
from models.color import Color
from models.events import EventType
from models.events.zone_static_events import ZoneStaticStateChangedEvent
from models.frame import SingleZoneFrame
from engine.frame_manager import FrameManager
from services.event_bus import EventBus
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
    
    def __init__(
        self, 
        frame_manager: FrameManager, 
        event_bus: EventBus
    ):
        self.frame_manager = frame_manager

        # ---- context (pushed from controller) ----
        self._edit_mode: bool = False
        self._selected_zone_id: Optional[ZoneID] = None
        self._render_mode: Optional[ZoneRenderMode] = None
        self._zone_is_on: bool = True
        self._zone_color: Optional[Color] = None
        self._zone_brightness: int = 100  # 0–100
        
        self._restart_scheduled = False
        
        # ---- task state ----
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

        event_bus.subscribe(
            EventType.ZONE_STATIC_STATE_CHANGED,
            self._on_zone_state_changed
        )

    # ------------------------------------------------------------------
    # Context update API (called by LightingController)
    # ------------------------------------------------------------------

    def on_selected_zone_changed(self, zone_id):
        if self._selected_zone_id == zone_id:
            return
        self._selected_zone_id = zone_id
        # log.debug(f"Indicator: selected zone → {zone_id.name}")
        self._schedule_restart()

    def on_zone_render_mode_changed(self, mode):
        if self._render_mode == mode:
            return
        self._render_mode = mode
        # log.debug(f"Indicator: render mode → {mode.name}")
        self._schedule_restart()

    def on_edit_mode_changed(self, enabled):
        if self._edit_mode == enabled:
            return
        self._edit_mode = enabled
        # log.debug(f"Indicator: edit mode → {enabled}")
        self._schedule_restart()

    def _on_zone_state_changed(self, e: ZoneStaticStateChangedEvent) -> None:
        """Handle zone state change events from EventBus"""
        if e.zone_id != self._selected_zone_id:
            return

        changed = False
        if e.color is not None:
            self._zone_color = e.color
            changed = True

        if e.brightness is not None:
            self._zone_brightness = e.brightness
            changed = True

        if e.is_on is not None:
            self._zone_is_on = e.is_on
            changed = True

        # Restart indicator to use updated values
        if changed:
            log.debug(f"Zone {e.zone_id.name} state changed, restarting indicator")
            self._restart_if_active()
        
    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------
    def _schedule_restart(self):
        if self._restart_scheduled:
            return

        self._restart_scheduled = True
        asyncio.create_task(self._restart_soon())
    
    async def _restart_soon(self):
        await asyncio.sleep(0)  # pozwól event loopowi zebrać zmiany
        self._restart_scheduled = False
        self._restart_if_active()
        
    def _start(self) -> None:
        if self._running:
            return

        if not self._can_run():
            log.info("Indicator cant run")
            return

        # log.info("Indicator starting")
        self._running = True
        
        self._task = asyncio.create_task(self._loop())
         
        # create_tracked_task(
        #     self._loop(),
        #     category=TaskCategory.RENDER,
        #     description=f"Selected Zone Indicator ({self._selected_zone_id.name if self._selected_zone_id else 'unknown'})"
        # )

    def _stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        # log.info("Indicator stopped")

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
        log.debug(f"Indicator restarting for {self._selected_zone_id.name if self._selected_zone_id else '?'} (mode={self._render_mode.name if self._render_mode else '?'})")
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
        try:
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
        except asyncio.CancelledError:
            pass
        
        
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
        
            if not self._selected_zone_id:
                log.warn("Selected zone id empty")
                return
            
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
        if not self._selected_zone_id:
            log.warn("Selected zone id empty")
            return
        
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
        if not self._selected_zone_id:
            log.warn("Selected zone id empty")
            return
        
        frame = SingleZoneFrame(
            zone_id=self._selected_zone_id,
            color=self.OFF_ZONE_COLOR,
            priority=FramePriority.PULSE,
            source=FrameSource.PULSE,
            ttl=self.OFF_ZONE_TTL,
        )

        await self.frame_manager.push_frame(frame)
        await asyncio.sleep(self.OFF_ZONE_TTL)