"""
LightingController - Main dispatcher and coordinator

Responsibilities:
- Handle user input (encoder, buttons, keyboard)
- Coordinate render mode transitions
- Delegate runtime behavior to mode controllers
- Synchronize selected zone indicator

Does NOT:
- Start/stop animations directly
- Push frames directly
- Mutate zone state directly (except via ZoneService)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from animations.engine import AnimationEngine
from models.domain.zone import ZoneCombined
from models.events.sources import EncoderSource
from models.enums import ButtonID, ZoneRenderMode
from models.events.types import EventType
from models.events import (
    EncoderRotateEvent,
    EncoderClickEvent,
    ButtonPressEvent,
    KeyboardKeyPressEvent,
    ZoneAnimationChangedEvent,
    ZoneRenderModeChangedEvent,
)
from utils.logger import get_logger, LogCategory
from utils.serialization import Serializer
from services import ServiceContainer

from controllers.led_controller.static_mode_controller import StaticModeController
from controllers.led_controller.animation_mode_controller import AnimationModeController
from controllers.led_controller.frame_playback_controller import FramePlaybackController
from zone_layer.selected_zone_indicator import SelectedZoneIndicator

if TYPE_CHECKING:
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
        service_container: "ServiceContainer"
    ):
        self.config_manager = service_container.config_manager
        self.event_bus = service_container.event_bus
        self.services = service_container
        
        self.zone_service = service_container.zone_service
        self.animation_service = service_container.animation_service
        self.app_state_service = service_container.app_state_service
        self.frame_manager = service_container.frame_manager

        # Create and attach animation engine
        # Use first available led channel from FrameManager (all channels have same zone mappings)
        if not self.frame_manager.led_channels:
            raise ValueError("No led channels registered with FrameManager")

        log.info("Initializing animation engine")
        self.animation_engine = AnimationEngine(
            frame_manager=self.frame_manager,
            zone_service=self.zone_service,
            event_bus=self.event_bus
        )

        log.info("Initializing static mode controller")
        self.static_mode_controller = StaticModeController(
            services=self.services
        )

        log.info("Initializing animation mode controller")
        self.animation_mode_controller = AnimationModeController(
            event_bus=self.event_bus,
            services=self.services,
            animation_engine=self.animation_engine
        )
        
        self.selected_zone_indicator = SelectedZoneIndicator(
            frame_manager=self.frame_manager,
            event_bus=self.event_bus
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
    # Initialization
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _initialize_animation_parameters(self, animation_id):
        """
        Initialize animation parameters with defaults from animation class.
        Returns dict of parameters with default values from animation PARAMS.
        """
        parameters = {}
        animation_class = self.animation_engine.ANIMATIONS.get(animation_id)

        if animation_class:
            for param_id, param_def in animation_class.PARAMS.items():
                parameters[param_id] = param_def.default

        return parameters

    # ------------------------------------------------------------------
    # MODE MANAGEMENT
    # ------------------------------------------------------------------

    async def _initialize_zones(self):
        """
        Initialize controllers according to persisted zone state.
        """
        log.info("Initializing zone controllers...")

        await self.static_mode_controller.initialize()
        await self.animation_mode_controller.initialize()

        # Initialize the active zone indicator with the selected zone
        selected_zone = self.zone_service.get_selected_zone()
        if selected_zone:
            self._sync_indicator(selected_zone)
        
        log.info("Zone controllers initialization coordinated")
    
    # ------------------------------------------------------------------
    # Event registration
    # ------------------------------------------------------------------

    def _register_events(self):
        self.event_bus.subscribe(EventType.ENCODER_ROTATE, self._handle_encoder_rotate)
        self.event_bus.subscribe(EventType.ENCODER_CLICK, self._handle_encoder_click)
        self.event_bus.subscribe(EventType.BUTTON_PRESS, self._handle_button)
        self.event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, self._handle_keyboard_keypress)

        # Zone animation and mode changes
        self.event_bus.subscribe(EventType.ZONE_ANIMATION_CHANGED, self._handle_zone_animation_changed)  # type: ignore
        self.event_bus.subscribe(EventType.ZONE_RENDER_MODE_CHANGED, self._handle_zone_render_mode_changed)  # type: ignore

        log.info("LightingController subscribed to EventBus")

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

    async def _handle_keyboard_keypress(self, e: KeyboardKeyPressEvent):
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
            await self._set_selected_zone_render_mode_async(ZoneRenderMode.STATIC)
        elif key == 'X':
            log.info("Switching selected zone to ANIMATION mode (X pressed)")
            await self._set_selected_zone_render_mode_async(ZoneRenderMode.ANIMATION)


    # ------------------------------------------------------------------
    # Zone events (DOMAIN → RUNTIME)
    # ------------------------------------------------------------------

    async def _handle_zone_render_mode_changed(self, event: ZoneRenderModeChangedEvent) -> None:
        """
        Handle render mode changes for a zone.

        When a zone switches modes:
        - From ANIMATION → STATIC: Stop the animation
        - To ANIMATION: Start animation is handled by animation change event
        """
        zone = self.zone_service.get_zone(event.zone_id)
        if not zone:
            log.warn(f"Render mode changed event for unknown zone: {event.zone_id}")
            return
        
        
        log.info(
            "Zone render mode changed",
            zone=zone.config.display_name,
            old=event.old.name,
            new=event.new.name,
        )
        
        zone_name = zone.config.display_name
        if event.old == event.new:
            log.warn(f"Zone {zone_name} is already in {event.new.name} mode. Skipping...")
            return
        
        log.info(f"Zone {zone_name} will leave {event.old.name} mode and enter {event.new.name} mode.")

        # Exit old render mode
        if event.old == ZoneRenderMode.ANIMATION:
            await self.animation_mode_controller.leave_zone(zone)
        elif event.old == ZoneRenderMode.STATIC:
            self.static_mode_controller.leave_zone(zone)
            
        # And enter new render mode
        if event.new == ZoneRenderMode.ANIMATION:
            await self.animation_mode_controller.enter_zone(zone)
        elif event.new == ZoneRenderMode.STATIC:
            self.static_mode_controller.enter_zone(zone)
            
        self._sync_indicator(zone)
        
    async def _handle_zone_animation_changed(self, event: ZoneAnimationChangedEvent) -> None:
        """
        Handle animation changes when switching between animations in ANIMATION mode.
        Restarts the animation (stop old, start new) when animation ID changes.

        Uses async sequencing to ensure old animation fully stops before new one starts,
        preventing race conditions where enter_zone could run before leave_zone completes.
        """
        try:
            zone = self.zone_service.get_zone(event.zone_id)
            if not zone:
                log.warn(f"Animation changed event for unknown zone: {event.zone_id}")
                return

            # Only handle if zone is in ANIMATION mode
            if zone.state.mode != ZoneRenderMode.ANIMATION:
                log.debug(f"Zone {event.zone_id.name} not in ANIMATION mode, skipping animation restart")
                return

            # Get current animation state
            anim_state = zone.state.animation
            if not anim_state:
                log.warn("ZONE_ANIMATION_CHANGED but no animation state present")
                return

            # Restart animation: stop old, start new (properly sequenced)
            # This handles the case of switching from one animation to another while already in ANIMATION mode
            log.info(
                "Restarting animation",
                zone=zone.config.display_name,
                animation=event.animation_id.name,
            )

            # Stop the old animation (await to ensure completion before starting new)
            await self.animation_mode_controller.leave_zone(zone)

            # Start the new animation (after old one fully stopped)
            await self.animation_mode_controller.enter_zone(zone)

        except Exception as e:
            log.error(
                f"Failed to restart animation for zone {event.zone_id.name}",
                exc_info=True,
                error=str(e),
                animation=event.animation_id.name
            )
            # Continue gracefully instead of crashing


    
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
        if not self.app_state_service.get_state().edit_mode:
            log.info("Selector click ignored when not in edit mode")
            return

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
            self.animation_mode_controller.cycle_param()

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
            self.static_mode_controller.publish_zone_frame(zone)

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
        
    
    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def _set_selected_zone_render_mode_async(self, target_mode: ZoneRenderMode):
        """
        Set the render mode of the selected selected zone.

        This is called directly by keyboard events (Z - static/X - animation).
        """
        zone = self.zone_service.get_selected_zone()
        if not zone:
            log.warn("No zone selected for SetZoneMode")
            return

        zone_name = zone.config.display_name
        zone_mode = zone.state.mode
        if zone_mode == target_mode:
            log.info(f"Zone {zone_name} already in mode {target_mode.name}")
            return
        
        log.info(f"Setting zone {zone_name} render mode:  {zone_mode} → {target_mode}")

        self.zone_service.set_render_mode(zone.config.id, target_mode)
        
    async def _set_zone_render_mode_async(self, zone: ZoneCombined, target_mode: ZoneRenderMode):
        zone_id = zone.config.id
        zone_render_mode = zone.state.mode

        if zone_render_mode == target_mode:
            log.info(f"Zone {zone_id.name} already in mode {target_mode.name}")
            return

        log.info(f"Zone {zone_id.name} render mode:  {zone_render_mode.name} → {target_mode.name}")

        # Update state through service (handles persistence and event publishing)
        self.zone_service.set_render_mode(zone_id, target_mode)        

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
