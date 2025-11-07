"""
Transition Service

Manages smooth LED state transitions across the entire system.
Handles transitions for app lifecycle, mode switches, animation changes, etc.


Adds:
- transition_lock (prevents concurrent transitions)
- is_active() to check ongoing transition
- wait_for_idle() for synchronization
- prepare_for_animation_switch() to safely fade out + stop current animation

This version preserves existing public methods and presets, 
so other modules continue to work unchanged.

"""

import asyncio
from typing import Optional, List, Tuple, Callable
from models.transition import TransitionType, TransitionConfig
from models.enums import LogLevel, LogCategory
from utils.logger import get_category_logger

log = get_category_logger(LogCategory.SYSTEM)


class TransitionService:
    """
    Service for managing LED state transitions

    Provides smooth transitions between any LED states in the system:
    - App startup (darkness → saved state)
    - App shutdown (current state → darkness)
    - Mode switches (STATIC ↔ ANIMATION)
    - Animation changes (breathe → snake)
    - Power toggles (on ↔ off)

    Includes presets for common transition scenarios with sensible defaults.

    Example:
        service = TransitionService(strip)
        
        # App startup with smooth fade-in
        await service.fade_in_from_black(service.STARTUP)
        
        # Mode switch with quick fade
        await service.fade_to_new_state(
            new_state_setter=lambda: controller.apply_static_colors(),
            config=service.MODE_SWITCH
        )
    """

    # === Transition Presets ===

    STARTUP = TransitionConfig(type=TransitionType.FADE, duration_ms=2000, steps=30)
    SHUTDOWN = TransitionConfig(type=TransitionType.FADE, duration_ms=600, steps=15)
    MODE_SWITCH = TransitionConfig(type=TransitionType.FADE, duration_ms=400, steps=15)
    ANIMATION_SWITCH = TransitionConfig(type=TransitionType.FADE, duration_ms=400, steps=15)
    ZONE_CHANGE = TransitionConfig(type=TransitionType.NONE)
    POWER_TOGGLE = TransitionConfig(type=TransitionType.FADE, duration_ms=400, steps=12)


    def __init__(self, strip):
        """
        Initialize transition service

        Args:
            strip: ZoneStrip instance with LED control methods
        """
        self.strip = strip
        
        self._transition_lock = asyncio.Lock()  # Prevent overlapping transitions

        log.info("TransitionService initialized",
            startup_ms=self.STARTUP.duration_ms,
            mode_switch_ms=self.MODE_SWITCH.duration_ms)

    
    def is_active(self) -> bool:
        """Return True if any transition is currently running"""
        return self._transition_lock.locked()

    async def wait_for_idle(self):
        """Wait until all transitions are complete"""
        while self._transition_lock.locked():
            await asyncio.sleep(0.01)

    async def prepare_for_animation_switch(self, engine):
        """
        Fade out the current animation if running and stop it cleanly.

        NOTE: Caller should call wait_for_idle() BEFORE calling this method.
        Do NOT call wait_for_idle() here - would cause deadlock (lock inside lock).

        Returns:
            Captured frame from before fade-out (may be empty list)
        """
        async with self._transition_lock:
            # DON'T call wait_for_idle() here - caller already waited

            current_frame = []
            if hasattr(engine, "is_running") and engine.is_running():
                log.info("Preparing animation switch (fade out current)")

                # Capture frame BEFORE fade
                if hasattr(engine.strip, "get_frame"):
                    try:
                        current_frame = engine.strip.get_frame() or []
                    except Exception as e:
                        log.warn(f"Failed to capture frame before transition: {e}")

                # Fade out (using no-lock version since we're already inside lock)
                await self._fade_out_no_lock(self.ANIMATION_SWITCH)

                # Stop engine WITHOUT calling engine.stop() (to avoid recursive transition)
                # Manually cleanup animation task
                if engine.current_animation:
                    engine.current_animation.stop()

                if engine.animation_task:
                    engine.animation_task.cancel()
                    try:
                        await engine.animation_task
                    except asyncio.CancelledError:
                        pass
                    engine.animation_task = None

                engine.current_animation = None
                engine.current_id = None

            return current_frame

    # ============================================================
    # Core transition methods
    # ============================================================

    async def _fade_out_no_lock(self, config: TransitionConfig):
        """
        Internal fade out implementation without lock (for use inside locked context).

        Args:
            config: Transition configuration
        """
        if config.type == TransitionType.NONE:
            return  # No transition

        if not hasattr(self.strip, "get_frame"):
            log.warn("Strip doesn't support get_frame(), using clear()")
            self.strip.clear()
            await asyncio.sleep(config.duration_ms / 1000)
            return

        current_frame = self.strip.get_frame()
        if not current_frame:
            log.debug("No frame to fade out")
            return

        step_delay = config.duration_ms / 1000 / config.steps
        log.debug(f"Fade out: {config.duration_ms}ms, {config.steps} steps")

        # Gradually reduce brightness
        for step in range(config.steps, -1, -1):
            progress = step / config.steps
            factor = config.ease_function(progress)

            for i, (r, g, b) in enumerate(current_frame):
                self.strip.set_pixel_color_absolute(
                    i,
                    int(r * factor),
                    int(g * factor),
                    int(b * factor),
                    show=False
                )
            self.strip.show()
            await asyncio.sleep(step_delay)

        log.debug("Fade out complete")

    async def fade_out(self, config: Optional[TransitionConfig] = None):
        """
        Fade out current LED state to black

        Captures current frame state and gradually reduces brightness to zero.
        Falls back to simple clear() if strip doesn't support get_frame().

        Args:
            config: Transition configuration (defaults to MODE_SWITCH preset)

        Example:
            >>> # Before mode switch
            >>> await transition_service.fade_out(TransitionService.MODE_SWITCH)
            >>> controller.switch_to_static_mode()
        """
        config = config or self.MODE_SWITCH

        async with self._transition_lock:
            await self._fade_out_no_lock(config)

    async def fade_in(
        self,
        target_frame: List[Tuple[int, int, int]],
        config: Optional[TransitionConfig] = None
    ):
        """
        Fade in from black to target LED state

        Gradually increases brightness from zero to target colors.

        Args:
            target_frame: List of (r, g, b) tuples for each pixel
            config: Transition configuration (defaults to MODE_SWITCH)

        Example:
            >>> target = [(255, 0, 0), (0, 255, 0), ...]
            >>> await transition_service.fade_in(target, TransitionService.STARTUP)
        """
        config = config or self.MODE_SWITCH

        if config.type == TransitionType.NONE:
            # Instant set
            for i, (r, g, b) in enumerate(target_frame):
                self.strip.set_pixel_color_absolute(i, r, g, b, show=False)
            self.strip.show()
            return

        
        async with self._transition_lock:
            
            step_delay = config.duration_ms / 1000 / config.steps
            log.debug(f"Fade in: {config.duration_ms}ms, {config.steps} steps")

            # Gradually increase brightness
            for step in range(config.steps + 1):
                progress = step / config.steps
                factor = config.ease_function(progress)

                for i, (r, g, b) in enumerate(target_frame):
                    self.strip.set_pixel_color_absolute(
                        i,
                        int(r * factor),
                        int(g * factor),
                        int(b * factor),
                        show=False
                    )
                self.strip.show()
                await asyncio.sleep(step_delay)

            log.debug("Fade in complete")

    async def fade_in_from_black(self, config: Optional[TransitionConfig] = None):
        """
        Fade in from black to current strip state

        Useful for app startup - assumes strip is already set to target colors
        (e.g., from saved state), temporarily clears it, then fades in.

        Args:
            config: Transition configuration (defaults to STARTUP)

        Example:
            >>> # At app startup
            >>> controller.restore_saved_state()  # Sets colors on strip
            >>> await transition_service.fade_in_from_black(TransitionService.STARTUP)
        """
        config = config or self.STARTUP

        if not hasattr(self.strip, 'get_frame'):
            log.warn("Strip doesn't support get_frame(), skipping fade")
            return

        # Capture target state
        target_frame = self.strip.get_frame()
        if not target_frame:
            log.debug("No frame to fade in")
            return

        # Clear to black
        self.strip.clear()

        # Fade in to target
        await self.fade_in(target_frame, config)

    async def fade_to_new_state(
        self,
        new_state_setter: Callable[[], None],
        config: Optional[TransitionConfig] = None
    ):
        """
        Transition from current state to new state with fade

        Sequence: fade out → apply new state → fade in

        Args:
            new_state_setter: Function that applies new LED state to strip
            config: Transition configuration (defaults to MODE_SWITCH)

        Example:
            >>> # Switch from ANIMATION to STATIC mode
            >>> await transition_service.fade_to_new_state(
            ...     new_state_setter=lambda: controller.apply_static_colors(),
            ...     config=TransitionService.MODE_SWITCH
            ... )
        """
        config = config or self.MODE_SWITCH

        # Fade out current state
        await self.fade_out(config)

        # Apply new state while dark
        new_state_setter()

        # Capture new state
        if hasattr(self.strip, 'get_frame'):
            new_frame = self.strip.get_frame()
            if new_frame:
                # Clear and fade in
                self.strip.clear()
                await self.fade_in(new_frame, config)

    async def crossfade(
        self,
        from_frame: List[Tuple[int, int, int]],
        to_frame: List[Tuple[int, int, int]],
        config: Optional[TransitionConfig] = None
    ):
        """
        Crossfade between two LED states

        Smoothly blends from one frame to another by interpolating RGB values
        for each pixel. No black frame - direct transition.

        Args:
            from_frame: Starting state - list of (r, g, b) tuples for each pixel
            to_frame: Target state - list of (r, g, b) tuples for each pixel
            config: Transition configuration (defaults to MODE_SWITCH)

        Example:
            >>> # Smooth transition from animation to static
            >>> current = strip.get_frame()
            >>> strip.apply_static_colors()  # Sets new state
            >>> target = strip.get_frame()
            >>> await transition_service.crossfade(current, target, config)
        """
        config = config or self.MODE_SWITCH

        if config.type == TransitionType.NONE:
            # Instant set to target frame
            for i, (r, g, b) in enumerate(to_frame):
                self.strip.set_pixel_color_absolute(i, r, g, b, show=False)
            self.strip.show()
            return

        if len(from_frame) != len(to_frame):
            log.warn(f"Frame size mismatch: {len(from_frame)} → {len(to_frame)}, using instant switch")
            for i, (r, g, b) in enumerate(to_frame):
                self.strip.set_pixel_color_absolute(i, r, g, b, show=False)
            self.strip.show()
            return

        async with self._transition_lock:
            step_delay = config.duration_ms / 1000 / config.steps
            log.info(f"Transition started: crossfade ({config.duration_ms}ms)")

            # Gradually interpolate between frames
            for step in range(config.steps + 1):
                progress = step / config.steps
                factor = config.ease_function(progress)

                for i, ((r1, g1, b1), (r2, g2, b2)) in enumerate(zip(from_frame, to_frame)):
                    # Linear interpolation for each color channel
                    r = int(r1 + (r2 - r1) * factor)
                    g = int(g1 + (g2 - g1) * factor)
                    b = int(b1 + (b2 - b1) * factor)

                    self.strip.set_pixel_color_absolute(i, r, g, b, show=False)

                self.strip.show()
                await asyncio.sleep(step_delay)

            log.info("Transition complete: crossfade")

    async def cut(self, config: Optional[TransitionConfig] = None):
        """
        Hard cut transition with brief black frame

        Instantly clears LEDs and waits for specified duration.
        Creates a brief "blink" effect.

        Args:
            config: Transition configuration (defaults to 100ms cut)

        Example:
            >>> # Quick cut before animation
            >>> cut_config = TransitionConfig(TransitionType.CUT, duration_ms=50)
            >>> await transition_service.cut(cut_config)
        """
        config = config or TransitionConfig(TransitionType.CUT, duration_ms=100)
        async with self._transition_lock:
            log.debug(f"Cut transition: {config.duration_ms}ms black")
            self.strip.clear()
            await asyncio.sleep(config.duration_ms / 1000)

