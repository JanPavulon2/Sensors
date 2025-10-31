"""
Transition Service

Manages smooth LED state transitions across the entire system.
Handles transitions for app lifecycle, mode switches, animation changes, etc.
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
        >>> service = TransitionService(strip)
        >>>
        >>> # App startup with smooth fade-in
        >>> await service.fade_in_from_black(service.STARTUP)
        >>>
        >>> # Mode switch with quick fade
        >>> await service.fade_to_new_state(
        ...     new_state_setter=lambda: controller.apply_static_colors(),
        ...     config=service.MODE_SWITCH
        ... )
    """

    # === Transition Presets ===
    # TEMPORARY: All set to NONE for testing - will enable gradually

    STARTUP = TransitionConfig(
        type=TransitionType.NONE
    )

    SHUTDOWN = TransitionConfig(
        type=TransitionType.NONE
    )

    MODE_SWITCH = TransitionConfig(
        type=TransitionType.NONE
    )

    ANIMATION_SWITCH = TransitionConfig(
        type=TransitionType.NONE
    )

    ZONE_CHANGE = TransitionConfig(
        type=TransitionType.NONE
    )

    POWER_TOGGLE = TransitionConfig(
        type=TransitionType.NONE
    )

    def __init__(self, strip):
        """
        Initialize transition service

        Args:
            strip: ZoneStrip instance with LED control methods
        """
        self.strip = strip
        log.info("TransitionService initialized",
            startup_ms=self.STARTUP.duration_ms,
            mode_switch_ms=self.MODE_SWITCH.duration_ms)

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

        if config.type == TransitionType.NONE:
            return  # No transition

        # Try to capture current state
        if not hasattr(self.strip, 'get_frame'):
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
                self.strip.set_pixel_color(
                    i,
                    int(r * factor),
                    int(g * factor),
                    int(b * factor)
                )
            self.strip.show()
            await asyncio.sleep(step_delay)

        log.debug("Fade out complete")

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
                self.strip.set_pixel_color(i, r, g, b)
            self.strip.show()
            return

        step_delay = config.duration_ms / 1000 / config.steps
        log.debug(f"Fade in: {config.duration_ms}ms, {config.steps} steps")

        # Gradually increase brightness
        for step in range(config.steps + 1):
            progress = step / config.steps
            factor = config.ease_function(progress)

            for i, (r, g, b) in enumerate(target_frame):
                self.strip.set_pixel_color(
                    i,
                    int(r * factor),
                    int(g * factor),
                    int(b * factor)
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
        log.debug(f"Cut transition: {config.duration_ms}ms black")
        self.strip.clear()
        await asyncio.sleep(config.duration_ms / 1000)
