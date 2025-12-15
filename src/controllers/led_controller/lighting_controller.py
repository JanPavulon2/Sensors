"""
LED Controller (Main Dispatcher)
Coordinates between static, animation, and lamp/power modes.
"""

import asyncio
from typing import TYPE_CHECKING
from animations.engine import AnimationEngine
from zone_layer.selected_zone_indicator import SelectedZoneIndicator
from models.enums import ButtonID, EncoderSource, ZoneRenderMode
from models.events import EventType
from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent, KeyboardKeyPressEvent
from utils.logger import get_logger, LogCategory
from utils.serialization import Serializer
from services import ServiceContainer

from controllers.led_controller.static_mode_controller import StaticModeController
from controllers.led_controller.animation_mode_controller import AnimationModeController
from controllers.led_controller.frame_playback_controller import FramePlaybackController

if TYPE_CHECKING:
    from managers import ConfigManager
    from hardware.gpio.gpio_manager import GPIOManager
    from services.event_bus import EventBus

log = get_logger().for_category(LogCategory.GENERAL)

class LightingController:
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
        service_container: "ServiceContainer"
    ):
        self.config_manager = config_manager
        self.event_bus = event_bus
        self.gpio_manager = gpio_manager
        self.services = service_container
        
        self.zone_service = service_container.zone_service
        self.animation_service = service_container.animation_service
        self.app_state_service = service_container.app_state_service
        self.frame_manager = service_container.frame_manager

        # Create and attach animation engine
        # Use first available zone strip from FrameManager (all strips have same zone mappings)
        if not self.frame_manager.zone_strips:
            raise ValueError("No zone strips registered with FrameManager")

        log.info("Initializing animation engine")
        self.animation_engine = AnimationEngine(
            frame_manager=self.frame_manager,
            zone_service=self.zone_service
        )

        log.info("Initializing static mode controller")
        # Initialize feature controllers with dependency injection
        self.static_mode_controller = StaticModeController(
            services=self.services
        )

        log.info("Initializing animation mode controller")
        self.animation_mode_controller = AnimationModeController(
            services=self.services,
            animation_engine=self.animation_engine
        )
        
        self.selected_zone_indicator = SelectedZoneIndicator(
            frame_manager=self.frame_manager,
            event_bus=event_bus
        )

        # TODO: Disabled - needs direct FrameManager rendering implementation
        # log.info("Initializing lamp white mode controller")
        # self.lamp_white_mode = LampWhiteModeController(
        #     services=self.services
        # )

        # TODO: Disabled - needs direct FrameManager rendering implementation
        # self.power_toggle = PowerToggleController(
        #     services=self.services,
        #     preview_panel=preview_panel_controller,
        #     animation_engine=self.animation_engine,
        #     static_mode_controller=self.static_mode_controller
        # )
        
        self.frame_playback_controller = FramePlaybackController(
            frame_manager=self.frame_manager,
            animation_engine=self.animation_engine,
            event_bus=self.event_bus
        )

        # Register event handlers
        self._register_events()

        # Initialize zones based on per-zone modes (fire-and-forget async task)
        asyncio.create_task(self._initialize_zones())

        log.info("LightingController initialized")

    # ------------------------------------------------------------------
    # MODE MANAGEMENT
    # ------------------------------------------------------------------

    async def _initialize_zones(self):
        """
        Coordinate initialization of all zone mode controllers.

        Calls initialize() on each subcontroller to handle their own startup logic:
        - StaticModeController.initialize(): Render all STATIC zones
        - AnimationModeController.initialize(): Start animations for ANIMATION zones

        Each controller is responsible for reading zones, submitting frames, starting
        animations, etc. This method just orchestrates the sequence.
        """
        log.info("Coordinating zone controller initialization...")

        # Static zones render immediately (await to ensure frames are submitted)
        await self.static_mode_controller.initialize()
        await self.animation_mode_controller.initialize()

        # Initialize the active zone indicator with the selected zone
        selected_zone = self.zone_service.get_selected_zone()
        if selected_zone:
            self._sync_indicator(selected_zone)
        
        log.info("Zone controller initialization coordinated")
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
        # elif btn == ButtonID.BTN2:  # TODO: Disabled - lamp_white_mode not implemented
        #     asyncio.create_task(self.lamp_white_mode.toggle())
        # elif btn == ButtonID.BTN3:  # TODO: Disabled - power_toggle not implemented
        #     asyncio.create_task(self.power_toggle.toggle())
        # elif btn == ButtonID.BTN4:
        #     asyncio.create_task(self._toggle_zone_mode())

    def _handle_keyboard_keypress(self, e: KeyboardKeyPressEvent):
        """Handle keyboard key presses for debug features and zone mode switching.

        Keyboard shortcuts:
        - F: Enter frame-by-frame mode (debug)
        - Z: Switch selected zone to STATIC mode
        - X: Switch selected zone to ANIMATION mode
        """
        key = e.key.upper()
        if key == 'F':
            log.info("Entering frame-by-frame mode (F pressed)")
            asyncio.create_task(self._enter_frame_by_frame_mode_async())
        elif key == 'Z':
            log.info("Switching selected zone to STATIC mode (Z pressed)")
            asyncio.create_task(self._set_zone_render_mode_async(ZoneRenderMode.STATIC))
        elif key == 'X':
            log.info("Switching selected zone to ANIMATION mode (X pressed)")
            asyncio.create_task(self._set_zone_render_mode_async(ZoneRenderMode.ANIMATION))

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
        selected_zone = self.zone_service.get_selected_zone()
        if not selected_zone:
            log.warn("No zone selected for selector rotation")
            return

        if not self.app_state_service.get_state().edit_mode:
            log.info("Modulator rotation ignored when not in edit mode")
            return
        
        self._cycle_zone_selection(delta)

    def _handle_selector_click(self):
        """
        Selector click: Reserved for future use.

        Zone render mode is currently toggled via keyboard (Z=STATIC, X=ANIMATION).
        This method is a placeholder for per-zone mode toggle via selector.
        """
        # TODO: Implement selector-based mode toggle if needed in future

    def _handle_modulator_rotation(self, delta: int):
        """
        Modulator rotation: Adjust parameter based on selected zone's mode.

        Per-zone mode: Routes to appropriate controller based on zone's mode
        - STATIC zone: Adjust zone parameters (color, brightness)
        - ANIMATION zone: Adjust animation parameters (speed, intensity)
        """
        if not self.app_state_service.get_state().edit_mode:
            log.info("Modulator rotation ignored when not in edit mode")
            return

        selected_zone = self.zone_service.get_selected_zone()
        if not selected_zone:
            log.warn("No zone selected for modulator rotation")
            return

        if selected_zone.state.mode == ZoneRenderMode.STATIC:
            self.static_mode_controller.adjust_selected_target(delta)
        elif selected_zone.state.mode == ZoneRenderMode.ANIMATION:
            self.animation_mode_controller.adjust_param(delta)

    def _handle_modulator_click(self):
        """
        Modulator click: Cycle parameter based on selected zone's mode.
        """
        
        if not self.app_state_service.get_state().edit_mode:
            log.info("Modulator click ignored when not in edit mode")
            return

        selected_zone = self.zone_service.get_selected_zone()
        if not selected_zone:
            log.warn("No zone selected for modulator click")
            return

        if selected_zone.state.mode == ZoneRenderMode.STATIC:
            self.static_mode_controller.cycle_edit_target()
        elif selected_zone.state.mode == ZoneRenderMode.ANIMATION:
            self.animation_mode_controller.cycle_parameter()

    def _cycle_zone_selection(self, delta: int):
        """
        Cycle to next/previous zone and render all STATIC zones.

        Implements zone selection logic (moved from StaticModeController to honor SRP).
        Delegates rendering to StaticModeController.

        Args:
            delta: +1 for next zone, -1 for previous zone
        """
        zones = self.zone_service.get_all()
        if not zones:
            log.warn("No zones available for cycling")
            return
        
        state = self.app_state_service.get_state()
        
        new_index = (state.selected_zone_index + delta) % len(zones)
        self.app_state_service.set_selected_zone_index(new_index)
        
        zone = zones[new_index]
        log.info(
            "Selected zone changed",
            zone=zone.config.display_name,
            mode=zone.state.mode.name,
            is_on=zone.state.is_on,
        )
        
        self._sync_indicator(zone)
        
        if zone.state.mode == ZoneRenderMode.STATIC:
            self.static_mode_controller.submit_zone(zone)

    def _sync_indicator(self, zone):
        self.selected_zone_indicator.on_selected_zone_changed(zone.id)
        self.selected_zone_indicator.on_zone_render_mode_changed(zone.state.mode)
        self.selected_zone_indicator.on_edit_mode_changed(
            self.app_state_service.get_state().edit_mode
        )

        # initial state snapshot
        self.selected_zone_indicator._zone_color = zone.state.color
        self.selected_zone_indicator._zone_brightness = zone.brightness
        self.selected_zone_indicator._zone_is_on = zone.state.is_on
        
    def _toggle_edit_mode(self):
        """Toggle edit mode and notify controllers"""
        edit_mode_enabled = not self.app_state_service.get_state().edit_mode
        self.app_state_service.set_edit_mode(edit_mode_enabled)

        self.selected_zone_indicator.on_edit_mode_changed(edit_mode_enabled)
        
    async def _set_zone_render_mode_async(self, target_mode: ZoneRenderMode):
        """
        Set the render mode of the selectedly selected zone.

        This is called directly by keyboard events (Z - static/X - animation).
        """
        selected_zone = self.zone_service.get_selected_zone()
        if not selected_zone:
            log.warn("No zone selected for SetZoneMode")
            return

        zone_id = selected_zone.config.id
        selected_zone_render_mode = selected_zone.state.mode

        if selected_zone_render_mode == target_mode:
            log.info(f"Zone {zone_id.name} already in mode {target_mode.name}")
            return

        log.info(f"Zone {zone_id.name} render mode:  {selected_zone_render_mode.name} → {target_mode.name}")

        if selected_zone_render_mode == ZoneRenderMode.ANIMATION:
            await self.animation_engine.stop_for_zone(zone_id)
        
        # Update state
        selected_zone.state.mode = target_mode
        self.zone_service.save_state()

        self.selected_zone_indicator.on_zone_render_mode_changed(target_mode)
        
        # SETUP: Enter new mode after switching
        if target_mode == ZoneRenderMode.STATIC:
            log.debug(f"Entering STATIC mode for {zone_id.name}")
            self.static_mode_controller.submit_zone(selected_zone)

        elif target_mode == ZoneRenderMode.ANIMATION:
            log.debug(f"Entering ANIMATION mode for {zone_id.name}")

            # Auto-assign first animation if zone has none configured
            if not selected_zone.state.animation:
                available_animations = self.animation_service.get_all()
                if available_animations:
                    from models.domain.animation import AnimationState
                    first_anim_id = available_animations[0].id
                    selected_zone.state.animation = AnimationState(id=first_anim_id, parameter_values={})
                    log.info(
                        "Auto-assigned animation to zone entering ANIMATION mode",
                        zone=zone_id.name,
                        animation=first_anim_id.name,
                    )
                    # Persist auto-assigned animation immediately
                    self.zone_service.save_state()
                else:
                    log.error(f"No animations available to assign to zone {zone_id.name}")
                    return

            # Start animation on this zone
            anim_id = selected_zone.state.animation.id
            anim_params = selected_zone.state.animation.parameter_values

            # Build parameters for engine
            params = self.animation_service.build_params_for_zone(
                anim_id,
                anim_params,
                selected_zone
            )

            safe_params = Serializer.params_enum_to_str(params)
            await self.animation_engine.start_for_zone(zone_id, anim_id, safe_params)
            log.info(f"Started {anim_id.name} animation for zone {zone_id.name}")

    # ------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------

    async def _enter_frame_by_frame_mode_async(self):
        """Async wrapper to enter frame-by-frame mode for selectedly selected zone's animation."""
        # TODO: Phase 3 - Refactor to work with per-zone animations
        selected_zone = self.zone_service.get_selected_zone()
        if not selected_zone or not selected_zone.state.animation:
            log.warn("No animation on selected zone, cannot enter frame-by-frame mode")
            return

        anim_id = selected_zone.state.animation.id
        log.info(f"Entering frame-by-frame mode for animation: {anim_id.name} (to be implemented in Phase 3)")
        # TODO: Build params and call frame_playback_controller with per-zone parameters
