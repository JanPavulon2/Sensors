"""
LED Controller (Main Dispatcher)
Coordinates between static, animation, and lamp/power modes.
"""

import asyncio
from typing import TYPE_CHECKING
from animations.engine import AnimationEngine
from models.enums import MainMode, ButtonID, EncoderSource
from models.events import EventType
from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent
from utils.logger import get_logger, LogCategory, LogLevel

from controllers.led_controller.static_mode_controller import StaticModeController
from controllers.led_controller.animation_mode_controller import AnimationModeController
from controllers.led_controller.lamp_white_mode_controller import LampWhiteModeController
from controllers.led_controller.power_toggle_controller import PowerToggleController

if TYPE_CHECKING:
    from controllers.preview_panel_controller import PreviewPanelController
    from controllers.zone_strip_controller import ZoneStripController
    from services import ZoneService, AnimationService, ApplicationStateService
    from managers import ConfigManager
    from infrastructure import GPIOManager
    from services.event_bus import EventBus
    
log = get_logger()

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
        zone_strip_controller: "ZoneStripController"
    ):
        self.config_manager = config_manager
        self.event_bus = event_bus
        self.gpio_manager = gpio_manager
        self.zone_service = zone_service
        self.animation_service = animation_service
        self.app_state_service = app_state_service
        self.preview_panel_controller = preview_panel_controller
        self.zone_strip_controller = zone_strip_controller

        # Create and attach animation engine
        self.animation_engine = AnimationEngine(
            strip=self.zone_strip_controller.zone_strip,
            zones=self.zone_service.get_all()
        )
        
        # Load persistent state
        state = app_state_service.get_state()
        self.main_mode = state.main_mode
        self.edit_mode = state.edit_mode
        
        # Initialize feature controllers
        self.static_mode_controller = StaticModeController(self)
        self.animation_mode_controller = AnimationModeController(self)
        self.lamp_white_mode = LampWhiteModeController(self)
        self.power_toggle = PowerToggleController(self)
        
        # Register event handlers
        self._register_events()

        # Initialize zones based on current mode
        self._enter_mode(self.main_mode)

        log.info(LogCategory.SYSTEM, "LEDController initialized")

    # ------------------------------------------------------------------
    # MODE MANAGEMENT
    # ------------------------------------------------------------------

    def _enter_mode(self, mode: MainMode):
        """Enter specified mode (called on init and after mode toggle)"""
        if mode == MainMode.STATIC:
            self.static_mode_controller.enter_mode()
        else:
            self.animation_mode_controller.enter_mode()

    # ------------------------------------------------------------------
    # EVENT BUS SUBSCRIPTIONS
    # ------------------------------------------------------------------

    def _register_events(self):
        """Subscribe to all relevant hardware events."""
        self.event_bus.subscribe(EventType.ENCODER_ROTATE, self._handle_encoder_rotate)

        self.event_bus.subscribe(EventType.ENCODER_CLICK, self._handle_encoder_click)

        self.event_bus.subscribe(EventType.BUTTON_PRESS, self._handle_button)

        log.info(LogCategory.SYSTEM, "LEDController subscribed to EventBus")
        
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
            self._toggle_main_mode()
            
    # ------------------------------------------------------------------
    # ACTIONS (DISPATCH)
    # ------------------------------------------------------------------

    def _handle_selector_rotation(self, delta: int):
        if self.main_mode == MainMode.STATIC:
            self.static_mode_controller.change_zone(delta)
        else:
            self.animation_mode_controller.select_animation(delta)
            
    def _handle_selector_click(self):
        if self.main_mode == MainMode.STATIC:
            log.info(LogCategory.SYSTEM, "Selector click ignored in STATIC mode")
        else:
            asyncio.create_task(self.animation_mode_controller.toggle_animation())
            
    def _handle_modulator_rotation(self, delta: int):
        if not self.edit_mode:
            log.info(LogCategory.SYSTEM, "Modulator rotation ignored when not in edit mode")
            return
        if self.main_mode == MainMode.STATIC:
            self.static_mode_controller.adjust_param(delta)
        else:
            self.animation_mode_controller.adjust_param(delta)
        
    def _handle_modulator_click(self):
        if not self.edit_mode:
            return
        if self.main_mode == MainMode.STATIC:
            self.static_mode_controller.cycle_parameter()
        else: 
            self.animation_mode_controller.cycle_param()
        
    def _toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.app_state_service.set_edit_mode(self.edit_mode)
        
        if self.main_mode == MainMode.STATIC:
            self.static_mode_controller.on_edit_mode_change(self.edit_mode)
        else:
            self.animation_mode_controller.on_edit_mode_change(self.edit_mode)
        
    def _toggle_main_mode(self):
        """Switch between STATIC ↔ ANIMATION"""
        next_mode = (
            MainMode.ANIMATION
            if self.main_mode == MainMode.STATIC
            else MainMode.STATIC
        )

        self.main_mode = next_mode
        self.app_state_service.set_main_mode(next_mode)

        self._enter_mode(next_mode)

        log.info(LogCategory.SYSTEM, f"Switched to {next_mode.name} mode")
        
        
    # ------------------------------------------------------------------
    # CORE OPERATIONS
    # ------------------------------------------------------------------
    def clear_all(self) -> None:
        """Turn off all LEDs (both preview and strip)."""
        self.zone_strip_controller.zone_strip.clear()
        self.preview_panel_controller.clear()
        log.info(LogCategory.SYSTEM, "All LEDs cleared")

    async def stop_all(self) -> None:
        """Stop all async operations gracefully."""
        log.debug(LogCategory.SYSTEM, "Stopping animation engine...")
        await self.animation_engine.stop()

        log.debug(LogCategory.SYSTEM, "Clearing all LEDs...")
        self.clear_all()

        log.debug(LogCategory.SYSTEM, "LEDController stopped.")