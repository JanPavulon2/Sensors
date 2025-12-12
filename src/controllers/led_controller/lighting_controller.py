"""
LED Controller (Main Dispatcher)
Coordinates between static, animation, and lamp/power modes.
"""

import asyncio
from typing import TYPE_CHECKING, Dict
from animations.engine_v2 import AnimationEngine
from zone_layer.active_zone_indicator import ActiveZoneIndicator
from models.color import Color
from models.enums import ButtonID, EncoderSource, AnimationID, ZoneRenderMode
from models.events import EventType
from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent, KeyboardKeyPressEvent
from models.frame_v2 import SingleZoneFrame
from models.enums import FramePriority, FrameSource
from utils.logger import get_logger, LogCategory
from utils.serialization import Serializer
from services import ServiceContainer

from controllers.led_controller.static_mode_controller import StaticModeController
from controllers.led_controller.animation_mode_controller import AnimationModeController
from controllers.led_controller.lamp_white_mode_controller import LampWhiteModeController
from controllers.led_controller.power_toggle_controller import PowerToggleController
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

        first_strip = self.frame_manager.zone_strips[0]

        log.info("Initializing animation engine")
        self.animation_engine = AnimationEngine(
            frame_manager=self.frame_manager,
            zone_service=self.zone_service
        )

        # Load persistent state
        state = self.app_state_service.get_state()
        self.edit_mode = state.edit_mode
        preview_panel_controller = None


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
        
        self.active_zone_indicator = ActiveZoneIndicator(
            frame_manager=self.frame_manager)

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

        # Initialize zones based on per-zone modes
        self._initialize_zones()

        log.info("LightingController initialized")

    # ------------------------------------------------------------------
    # MODE MANAGEMENT
    # ------------------------------------------------------------------

    def _initialize_zones(self):
        """
        Coordinate initialization of all zone mode controllers.

        Calls initialize() on each subcontroller to handle their own startup logic:
        - StaticModeController.initialize(): Render all STATIC zones
        - AnimationModeController.initialize(): Start animations for ANIMATION zones

        Each controller is responsible for reading zones, submitting frames, starting
        animations, etc. This method just orchestrates the sequence.
        """
        log.info("Coordinating zone controller initialization...")

        # Static zones render immediately
        self.static_mode_controller.initialize()

        # Animated zones start asynchronously
        asyncio.create_task(self.animation_mode_controller.initialize())

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
        - Z: Switch current zone to STATIC mode
        - X: Switch current zone to ANIMATION mode
        - C: Switch current zone to OFF mode
        """
        key = e.key.upper()
        if key == 'F':
            log.info("Entering frame-by-frame mode (F pressed)")
            asyncio.create_task(self._enter_frame_by_frame_mode_async())
        elif key == 'Z':
            log.info("Switching current zone to STATIC mode (Z pressed)")
            asyncio.create_task(self._set_zone_render_mode_async(ZoneRenderMode.STATIC))
        elif key == 'X':
            log.info("Switching current zone to ANIMATION mode (X pressed)")
            asyncio.create_task(self._set_zone_render_mode_async(ZoneRenderMode.ANIMATION))
        elif key == 'C':
            log.info("Switching current zone to OFF mode (C pressed)")
            asyncio.create_task(self._set_zone_render_mode_async(ZoneRenderMode.OFF))

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
        current_zone = self.zone_service.get_selected_zone()
        if not current_zone:
            log.warn("No zone selected for selector rotation")
            return

        if not self.edit_mode:
            log.info("Modulator rotation ignored when not in edit mode")
            return
        
        self._cycle_zone_selection(delta)

    def _handle_selector_click(self):
        """
        Selector click: Toggle zone mode or start/stop animation.

        Per-zone mode: Selector click behavior depends on zone's mode
        - STATIC zone: Toggle to ANIMATION mode (with auto-select first animation)
        - ANIMATION zone: Toggle to STATIC mode
        - OFF zone: Ignored
        """
        pass

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

        if current_zone.state.mode == ZoneRenderMode.STATIC:
            self.static_mode_controller.adjust_param(delta)
        elif current_zone.state.mode == ZoneRenderMode.ANIMATION:
            self.animation_mode_controller.adjust_param(delta)

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

        if current_zone.state.mode == ZoneRenderMode.STATIC:
            self.static_mode_controller.cycle_parameter()
        #elif current_zone.state.mode == ZoneRenderMode.ANIMATION:
        #    self.animation_mode_controller.cycle_param()

    def _toggle_edit_mode(self):
        """Toggle edit mode and notify controllers"""
        self.edit_mode = not self.edit_mode
        self.app_state_service.set_edit_mode(self.edit_mode)

        # Notify indicator of edit mode change
        self.active_zone_indicator.set_edit_mode(self.edit_mode)

        # Notify controllers of edit mode change (per-zone mode aware)
        self.static_mode_controller.on_edit_mode_change(self.edit_mode)
        self.animation_mode_controller.on_edit_mode_change(self.edit_mode)

    # ------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------

    async def _enter_frame_by_frame_mode_async(self):
        """Async wrapper to enter frame-by-frame mode for currently selected zone's animation."""
        # TODO: Phase 3 - Refactor to work with per-zone animations
        current_zone = self.zone_service.get_selected_zone()
        if not current_zone or not current_zone.state.animation:
            log.warn("No animation on selected zone, cannot enter frame-by-frame mode")
            return

        anim_id = current_zone.state.animation.id
        log.info(f"Entering frame-by-frame mode for animation: {anim_id.name} (to be implemented in Phase 3)")
        # TODO: Build params and call frame_playback_controller with per-zone parameters

    async def _set_zone_render_mode_async(self, target_mode: ZoneRenderMode):
        """
        Set the render mode of the currently selected zone.

        This is called directly by keyboard events (Z - static/X - animation/C - off).

        Properly handles cleanup of old mode before applying new mode by delegating
        to the mode controllers' enter_mode() and exit_mode() methods.
        """
        current_zone = self.zone_service.get_selected_zone()
        if not current_zone:
            log.warn("No zone selected for SetZoneMode")
            return

        zone_id = current_zone.config.id
        old_mode = current_zone.state.mode

        if old_mode == target_mode:
            log.info(f"Zone {zone_id.name} already in mode {target_mode.name}")
            return

        log.info(f"SetZoneMode: {zone_id.name} {old_mode.name} → {target_mode.name}")

        # CLEANUP: Exit old mode before switching
        if old_mode == ZoneRenderMode.ANIMATION:
            log.debug(f"Exiting ANIMATION mode for {zone_id.name}")
            # Stop only this zone's animation, let other zones keep animating
            await self.animation_engine.stop_for_zone(zone_id)

        elif old_mode == ZoneRenderMode.STATIC:
            log.debug(f"Exiting STATIC mode for {zone_id.name}")
            await self.static_mode_controller.exit_mode()

        # Update state
        current_zone.state.mode = target_mode
        self.zone_service.save_state()

        # Notify indicator of render mode change
        self.active_zone_indicator.set_render_mode(target_mode)

        # SETUP: Enter new mode after switching
        if target_mode == ZoneRenderMode.STATIC:
            log.debug(f"Entering STATIC mode for {zone_id.name}")
            self.static_mode_controller.enter_mode()

        elif target_mode == ZoneRenderMode.ANIMATION:
            log.debug(f"Entering ANIMATION mode for {zone_id.name}")
            # Start animation only for this zone, not all animation zones
            if current_zone.state.animation:
                anim_id = current_zone.state.animation.id
                anim_params = current_zone.state.animation.parameter_values

                # Build parameters for engine
                params = self.animation_service.build_params_for_zone(
                    anim_id,
                    anim_params,
                    current_zone
                )

                safe_params = Serializer.params_enum_to_str(params)
                await self.animation_engine.start_for_zone(zone_id, anim_id, safe_params)
                log.info(f"Started {anim_id.name} animation for zone {zone_id.name}")
            else:
                log.warn(f"Zone {zone_id.name} in ANIMATION mode but has no animation configured")

        # elif target_mode == ZoneRenderMode.OFF:
        #     log.debug(f"Entering OFF mode for {zone_id.name}")
        #     # OFF mode: ensure animation is stopped
        #     if self.animation_engine.is_running():
        #         await self.animation_engine.stop()

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

        # Get current zone index from app state
        current_state = self.app_state_service.get_state()
        current_index = current_state.current_zone_index

        # Cycle to next/previous zone
        new_index = (current_index + delta) % len(zones)
        old_zone_id = zones[current_index].config.id
        new_zone_id = zones[new_index].config.id

        # Update app state with new zone index
        self.app_state_service.set_current_zone_index(new_index)
        log.info("Cycled zone selection", from_zone=old_zone_id.name, to_zone=new_zone_id.name)

        # Notify indicator of zone change
        self.active_zone_indicator.set_active_zone(new_zone_id)

        # Sync preview to show selected zone
        # self.static_mode_controller._sync_preview()

    def cycle_param(self):
        log.warn("cycle_param() not implemented for AnimationModeController after refactor")
   
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
        if current_zone.state.mode == ZoneRenderMode.STATIC:
            next_mode = ZoneRenderMode.ANIMATION
        else:
            next_mode = ZoneRenderMode.STATIC

        # 2. Stop any animation running on this zone
        if self.animation_engine.is_running(current_zone.id):
            current_anim_id = self.animation_engine.get_current_animation_id(current_zone.id)
            log.debug(f"Stopping animation {current_anim_id.name if current_anim_id else '?'}")
            await self.animation_engine.stop_for_zone(zone_id)

        # 3. Update zone mode
        current_zone.state.mode = next_mode
        self.zone_service.save_state()
        log.info(f"Zone {zone_id.name} mode toggled to {next_mode.name}")

        # Notify indicator of render mode change
        self.active_zone_indicator.set_render_mode(next_mode)

        log.info(f"Zone {zone_id.name}: Switching to {next_mode.name} mode")
        
        # 4. Handle mode-specific setup
        if next_mode == ZoneRenderMode.STATIC:
            # Submit static zone frame
            asyncio.create_task(
                self.frame_manager.push_frame(SingleZoneFrame(
                    zone_id=current_zone.id,
                    color=current_zone.state.color,
                    priority=FramePriority.MANUAL,
                    source=FrameSource.STATIC,
                    ttl=1.5
                ))
            )
            
            self.static_mode_controller.enter_mode()
            
        else:
            # ANIMATION mode
            log.info(f"Zone {zone_id.name}: Switching to ANIMATION mode")
            self.animation_mode_controller.enter_mode()


    # ------------------------------------------------------------------
    # CORE OPERATIONS
    # ------------------------------------------------------------------
    def clear_all(self) -> None:
        """Turn off all LEDs by clearing all registered zone strips."""
        for strip in self.frame_manager.zone_strips:
            strip.clear()
        log.info("All LEDs cleared")

    async def stop_all(self) -> None:
        """Stop all async operations gracefully."""
        
        log.debug("Stopping animation engine...")
        await self.animation_engine.stop_all()

        log.debug("Stopping indicator engine...")
        await self.active_zone_indicator.stop_async()
        
        log.debug("Clearing all LEDs...")
        self.clear_all()

        log.debug("LEDController stopped.")
