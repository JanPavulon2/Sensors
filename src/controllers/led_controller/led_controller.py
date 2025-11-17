"""
LED Controller (Main Dispatcher)
Coordinates between static, animation, and lamp/power modes.
"""

import asyncio
from typing import TYPE_CHECKING
from animations.engine import AnimationEngine
from models.enums import MainMode, ButtonID, EncoderSource, AnimationID, ZoneMode
from models.events import EventType
from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent, KeyboardKeyPressEvent
from utils.logger import get_logger, LogCategory, LogLevel
from utils.serialization import Serializer
from engine import FrameManager
from services import ServiceContainer

from controllers.led_controller.static_mode_controller import StaticModeController
from controllers.led_controller.animation_mode_controller import AnimationModeController
from controllers.led_controller.lamp_white_mode_controller import LampWhiteModeController
from controllers.led_controller.power_toggle_controller import PowerToggleController
from controllers.led_controller.frame_playback_controller import FramePlaybackController

if TYPE_CHECKING:
    from controllers.preview_panel_controller import PreviewPanelController
    from controllers.zone_strip_controller import ZoneStripController
    from services import ZoneService, AnimationService, ApplicationStateService
    from managers import ConfigManager
    from infrastructure import GPIOManager
    from services.event_bus import EventBus
    from engine.frame_manager import FrameManager
    
log = get_logger().for_category(LogCategory.GENERAL)

class LEDController:
    """
    Main controller for LED behavior and modes.

    Responsibilities:
    - Orchestrates static, animation and lamp modes
    - Handles encoder and button input events
    - Owns animation engine and manages transitions
    - Coordinates between services (state, zone, animation)
    """

    def __init__(
        self,
        config_manager: "ConfigManager",
        event_bus: "EventBus",
        gpio_manager: "GPIOManager",
        zone_service: "ZoneService",
        animation_service: "AnimationService",
        app_state_service: "ApplicationStateService",
        preview_panel_controller: "PreviewPanelController",
        zone_strip_controller: "ZoneStripController",
        frame_manager: "FrameManager"
    ):
        self.config_manager = config_manager
        self.event_bus = event_bus
        self.gpio_manager = gpio_manager
        self.zone_service = zone_service
        self.animation_service = animation_service
        self.app_state_service = app_state_service
        self.preview_panel_controller = preview_panel_controller
        self.zone_strip_controller = zone_strip_controller

        self.frame_manager = frame_manager
        self.frame_manager.add_main_strip(self.zone_strip_controller.zone_strip)

        if self.preview_panel_controller.preview_panel._pixel_strip:
            self.frame_manager.add_preview_strip(self.preview_panel_controller.preview_panel)

        # Create and attach animation engine
        self.animation_engine = AnimationEngine(
            strip=self.zone_strip_controller.zone_strip,
            zones=self.zone_service.get_all(),
            frame_manager=self.frame_manager
        )
        
        # Load persistent state
        state = app_state_service.get_state()
        # Note: main_mode has been removed - zones now have individual modes
        # Keeping self.main_mode for backward compatibility during transition
        # TODO: Remove this after full per-zone migration
        self.main_mode = MainMode.STATIC  # Default fallback
        self.edit_mode = state.edit_mode

        # Create ServiceContainer for dependency injection
        services = ServiceContainer(
            zone_service=zone_service,
            animation_service=animation_service,
            app_state_service=app_state_service,
            frame_manager=frame_manager,
            event_bus=event_bus,
            color_manager=config_manager.color_manager
        )

        # Initialize feature controllers with dependency injection
        self.static_mode_controller = StaticModeController(
            services=services,
            strip_controller=zone_strip_controller,
            preview_panel=preview_panel_controller
        )
        self.animation_mode_controller = AnimationModeController(
            services=services,
            animation_engine=self.animation_engine,
            preview_panel=preview_panel_controller
        )
        self.lamp_white_mode = LampWhiteModeController(
            services=services,
            strip_controller=zone_strip_controller
        )
        self.power_toggle = PowerToggleController(
            services=services,
            strip_controller=zone_strip_controller,
            preview_panel=preview_panel_controller,
            animation_engine=self.animation_engine,
            static_mode_controller=self.static_mode_controller,
            main_mode_getter=lambda: self.main_mode
        )
        self.frame_playback_controller = FramePlaybackController(
            frame_manager=self.frame_manager,
            animation_engine=self.animation_engine,
            event_bus=self.event_bus
        )
        
        # Register event handlers
        self._register_events()

        # Initialize zones based on current mode
        self._enter_mode(self.main_mode)


        log.info("LEDController initialized")

    # ------------------------------------------------------------------
    # MODE MANAGEMENT
    # ------------------------------------------------------------------

    def _enter_mode(self, mode: MainMode):
        """Enter specified mode (called on init and after mode toggle)"""
        if mode == MainMode.STATIC:
            self.static_mode_controller.enter_mode()
        else:
            self.animation_mode_controller.enter_mode()

    async def start_frame_by_frame_debugging(self, animation_id: AnimationID, **params):
        """
        Start frame-by-frame debugging mode for animation.

        Allows stepping through animation frames one at a time using keyboard:
        - A: Previous frame
        - D: Next frame
        - SPACE: Play/Pause animation playback
        - Q: Exit frame-by-frame mode

        Args:
            animation_id: AnimationID to debug (defaults to current animation)
            **params: Animation parameters to override (e.g., ANIM_SPEED=50)

        Returns:
            When user presses Q to exit frame-by-frame mode

        Example:
            await led_controller.start_frame_by_frame_debugging(
                AnimationID.SNAKE,
                ANIM_SPEED=50
            )
        """
        log.info(f"Starting frame-by-frame debugging mode")

        # Use current animation if not specified
        if animation_id is None:
            current_anim = self.animation_service.get_current()
            if not current_anim:
                log.warn("No animation selected for frame-by-frame debugging")
                return
            animation_id = current_anim.config.id

        # Enter frame-by-frame mode (blocks until user presses Q)
        await self.frame_playback_controller.enter_frame_by_frame_mode(animation_id, **params)

    # ------------------------------------------------------------------
    # EVENT BUS SUBSCRIPTIONS
    # ------------------------------------------------------------------

    def _register_events(self):
        """Subscribe to all relevant hardware events."""
        self.event_bus.subscribe(EventType.ENCODER_ROTATE, self._handle_encoder_rotate)

        self.event_bus.subscribe(EventType.ENCODER_CLICK, self._handle_encoder_click)

        self.event_bus.subscribe(EventType.BUTTON_PRESS, self._handle_button)

        self.event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, self._handle_keyboard_keypress)

        log.info("LEDController subscribed to EventBus")
        
    # ------------------------------------------------------------------
    # EVENT HANDLING
    # ------------------------------------------------------------------

    def _handle_encoder_rotate(self, e: EncoderRotateEvent):
        if e.source == EncoderSource.SELECTOR:
            self._handle_selector_rotation(e.delta)
        elif e.source == EncoderSource.MODULATOR:
            self._handle_modulator_rotation(e.delta)
            
    def _handle_encoder_click(self, e: EncoderClickEvent):
        if e.source == EncoderSource.SELECTOR:
            self._handle_selector_click()
        elif e.source == EncoderSource.MODULATOR:
            self._handle_modulator_click()

    def _handle_button(self, e: ButtonPressEvent):
        btn = e.source
        if btn == ButtonID.BTN1:
            self._toggle_edit_mode()
        elif btn == ButtonID.BTN2:
            asyncio.create_task(self.lamp_white_mode.toggle())
        elif btn == ButtonID.BTN3:
            asyncio.create_task(self.power_toggle.toggle())
        elif btn == ButtonID.BTN4:
            asyncio.create_task(self._toggle_zone_mode())

    def _handle_keyboard_keypress(self, e: KeyboardKeyPressEvent):
        """Handle keyboard key presses for debug features."""
        key = e.key.upper()
        if key == 'F':
            log.info("Entering frame-by-frame mode (F pressed)")
            asyncio.create_task(self._enter_frame_by_frame_mode_async())

    async def _enter_frame_by_frame_mode_async(self):
        """Async wrapper to enter frame-by-frame mode for currently running animation."""
        current_anim = self.animation_service.get_current()
        if not current_anim:
            log.warn("No animation running, cannot enter frame-by-frame mode")
            return

        # Debug current animation with its current parameters
        anim_id = current_anim.config.id
        params = current_anim.build_params_for_engine()
        safe_params = Serializer.params_enum_to_str(params)

        log.info(f"Entering frame-by-frame mode for animation: {anim_id.name}")
        await self.start_frame_by_frame_debugging(anim_id, **safe_params)

    # ------------------------------------------------------------------
    # ACTIONS (DISPATCH)
    # ------------------------------------------------------------------

    def _handle_selector_rotation(self, delta: int):
        """
        Selector rotation: Context-aware behavior based on selected zone's mode.

        Per-zone mode architecture:
        - STATIC zone: Rotate to select different zones
        - ANIMATION zone: Rotate to cycle through animations
        - OFF zone: Rotate to select different zones
        """
        if not self.edit_mode:
            log.info("Selector rotation ignored when not in edit mode")
            return

        current_zone = self.zone_service.get_selected_zone()
        if not current_zone:
            log.warn("No zone selected for selector rotation")
            return

        # Context-aware routing based on selected zone's mode
        if current_zone.state.mode == ZoneMode.ANIMATION:
            # In ANIMATION mode: rotate to cycle animations
            self.animation_mode_controller.select_animation(delta)
        else:
            # In STATIC or OFF mode: rotate to select zones
            self.static_mode_controller.change_zone(delta)
            
    def _handle_selector_click(self):
        """
        Selector click: Route based on currently selected zone's mode.

        Per-zone mode: Selector click behavior depends on zone's mode
        - STATIC zone: Ignored (no click action in STATIC mode)
        - ANIMATION zone: Start/stop animation
        - OFF zone: Ignored
        """
        current_zone = self.zone_service.get_selected_zone()
        if not current_zone:
            log.warn("No zone selected for selector click")
            return

        if current_zone.state.mode == ZoneMode.ANIMATION:
            asyncio.create_task(self.animation_mode_controller.toggle_animation())
        else:
            log.info(f"Selector click ignored for {current_zone.state.mode.name} zone")
            
    def _handle_modulator_rotation(self, delta: int):
        """
        Modulator rotation: Adjust parameter based on selected zone's mode.

        Per-zone mode: Routes to appropriate controller based on zone's mode
        - STATIC zone: Adjust zone parameters (color, brightness)
        - ANIMATION zone: Adjust animation parameters (speed, intensity)
        - OFF zone: Ignored
        """
        if not self.edit_mode:
            log.info("Modulator rotation ignored when not in edit mode")
            return

        current_zone = self.zone_service.get_selected_zone()
        if not current_zone:
            log.warn("No zone selected for modulator rotation")
            return

        if current_zone.state.mode == ZoneMode.STATIC:
            self.static_mode_controller.adjust_param(delta)
        elif current_zone.state.mode == ZoneMode.ANIMATION:
            self.animation_mode_controller.adjust_param(delta)
        # For OFF mode, do nothing
        
    def _handle_modulator_click(self):
        """
        Modulator click: Cycle parameter based on selected zone's mode.

        Per-zone mode: Routes to appropriate controller based on zone's mode
        - STATIC zone: Cycle zone parameters (COLOR → BRIGHTNESS → ...)
        - ANIMATION zone: Cycle animation parameters (SPEED → INTENSITY → ...)
        - OFF zone: Ignored
        """
        if not self.edit_mode:
            log.info("Modulator click ignored when not in edit mode")
            return

        current_zone = self.zone_service.get_selected_zone()
        if not current_zone:
            log.warn("No zone selected for modulator click")
            return

        if current_zone.state.mode == ZoneMode.STATIC:
            self.static_mode_controller.cycle_parameter()
        elif current_zone.state.mode == ZoneMode.ANIMATION:
            self.animation_mode_controller.cycle_param()
        # For OFF mode, do nothing
        
    def _toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.app_state_service.set_edit_mode(self.edit_mode)
        
        if self.main_mode == MainMode.STATIC:
            self.static_mode_controller.on_edit_mode_change(self.edit_mode)
        else:
            self.animation_mode_controller.on_edit_mode_change(self.edit_mode)
        
    async def _toggle_zone_mode(self):
        """
        Toggle currently selected zone between STATIC ↔ ANIMATION mode.

        Per-zone architecture: Only affects the selected zone, not all zones.

        Flow:
        1. Get currently selected zone
        2. Stop any animations running on this zone
        3. Toggle zone mode (STATIC ↔ ANIMATION)
        4. Start animation if switching to ANIMATION, or render static color if STATIC
        """
        current_zone = self.zone_service.get_selected_zone()
        if not current_zone:
            log.warn("No zone selected for mode toggle")
            return

        zone_id = current_zone.config.id
        log.info(f"Toggling zone mode for {zone_id.name}...")

        # 1. Determine next mode
        if current_zone.state.mode == ZoneMode.STATIC:
            next_mode = ZoneMode.ANIMATION
        else:
            next_mode = ZoneMode.STATIC

        # 2. Stop any animation running on this zone
        if self.animation_engine.is_running():
            current_anim_id = self.animation_engine.get_current_animation_id()
            log.debug(f"Stopping animation {current_anim_id.name if current_anim_id else '?'}")
            await self.animation_engine.stop()

        # 3. Update zone mode
        current_zone.state.mode = next_mode
        self.zone_service.save_state()
        log.info(f"Zone {zone_id.name} mode toggled to {next_mode.name}")

        # 4. Handle mode-specific setup
        if next_mode == ZoneMode.STATIC:
            log.debug(f"Zone {zone_id.name}: Switching to STATIC mode")
            # Just render the static color - frame merging will handle it
            r, g, b = current_zone.get_rgb()
            self.zone_strip_controller.zone_strip.set_zone_color(zone_id, r, g, b)

            # Sync preview
            self.static_mode_controller._sync_preview()
            if self.edit_mode:
                self.static_mode_controller._start_pulse()

        else:
            # ANIMATION mode
            log.debug(f"Zone {zone_id.name}: Switching to ANIMATION mode")

            # Stop any pulse from STATIC mode before starting animation
            self.static_mode_controller._stop_pulse()

            current_anim = self.animation_service.get_current()

            # Auto-select first animation if none is selected
            if not current_anim:
                all_animations = self.animation_service.get_all()
                if all_animations:
                    first_anim_id = all_animations[0].config.id
                    self.animation_service.set_current(first_anim_id)
                    current_anim = self.animation_service.get_current()
                    log.info(f"Auto-selected first animation: {first_anim_id.name}")
                else:
                    log.warn("No animations available, cannot switch zone to ANIMATION mode")
                    # Revert the mode change since we can't start animation
                    current_zone.state.mode = ZoneMode.STATIC
                    self.zone_service.save_state()
                    return

            anim_id = current_anim.config.id
            params = current_anim.build_params_for_engine()
            safe_params = Serializer.params_enum_to_str(params)

            log.debug(f"Starting animation {anim_id.name} on zone {zone_id.name}")

            # Build excluded zones list: exclude ALL zones except the selected one
            # This ensures animation runs ONLY on the selected zone
            excluded_zone_ids = [
                z.config.id for z in self.zone_service.get_all()
                if z.config.id != zone_id
            ]

            # Start animation with proper exclusions
            await self.animation_engine.start(anim_id, excluded_zones=excluded_zone_ids, **safe_params)
            self.animation_mode_controller._sync_preview()
        
        
    # ------------------------------------------------------------------
    # CORE OPERATIONS
    # ------------------------------------------------------------------
    def clear_all(self) -> None:
        """Turn off all LEDs (both preview and strip)."""
        self.zone_strip_controller.zone_strip.clear()
        self.preview_panel_controller.clear()
        log.info("All LEDs cleared")

    async def stop_all(self) -> None:
        """Stop all async operations gracefully."""
        log.debug("Stopping animation engine...")
        await self.animation_engine.stop()

        log.debug("Clearing all LEDs...")
        self.clear_all()

        log.debug("LEDController stopped.")