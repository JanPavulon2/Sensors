"""
LED Controller - Business logic with state machine

Two-mode system for LED control:
- STATIC mode: Zone editing (select zones, adjust color/brightness)
- ANIMATION mode: Animation control (select animations, adjust speed/intensity)

Hardware:
- Preview Panel: GPIO 19, 8 LEDs, GRB (CJMCU-2812-8)
- LED Strip: GPIO 18, 45 pixels, BRG (WS2811)
  Zones: lamp, top, right, bottom, left, strip

Features:
- Color system using Color model (HUE, PRESET, RGB, WHITE modes)
- Zone-based control with independent brightness per zone
- Animation engine with live parameter updates
- Edit mode with pulsing indicator for current zone
- Lamp white mode for desk lamp functionality
"""

import time
import math
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from rpi_ws281x import ws, Color as RGBColor  # Rename to avoid conflict with models.Color
from components import PreviewPanel, ZoneStrip
from controllers import PreviewController
from utils.logger import get_logger, LogLevel, LogCategory
from utils.enum_helper import EnumHelper
from animations import AnimationEngine
from typing import cast
from models import Color, ColorMode, MainMode, PreviewMode, ParamID
from models.enums import ZoneID, AnimationID, EncoderSource, ButtonID
from models.events import EventType, EncoderRotateEvent, EncoderClickEvent
from managers import ConfigManager, ColorManager, AnimationManager, ParameterManager, HardwareManager
from services import DataAssembler, AnimationService, ZoneService, UISessionService
from services.event_bus import EventBus

log = get_logger()

class LEDController:
    """
    LED Controller with two-mode state machine

    Main Modes:
        - STATIC: Zone editing (selector cycles zones, modulator adjusts parameters)
        - ANIMATION: Animation control (selector cycles animations, modulator adjusts parameters)

    Control:
        - Selector encoder: Choose zone (STATIC) or animation (ANIMATION)
        - Modulator encoder: Adjust current parameter value
        - BTN1: Toggle edit mode (enables/disables editing)
        - BTN2: Quick lamp white mode toggle
        - BTN3: Power toggle (all zones on/off)
        - BTN4: Toggle between STATIC and ANIMATION modes

    Parameters (context-sensitive):
        - STATIC mode: ZONE_COLOR_HUE, ZONE_COLOR_PRESET, ZONE_BRIGHTNESS
        - ANIMATION mode: ANIM_SPEED, ANIM_INTENSITY

    Example:
        led = LEDController(config_manager, state)
        led.handle_selector_rotation(1)  # Next zone/animation
        led.handle_modulator_rotation(-1)  # Decrease current parameter
        led.toggle_main_mode()  # STATIC ↔ ANIMATION
    """


    def __init__(self, config_manager: ConfigManager, event_bus: EventBus):
        """
        Initialize LED Controller

        Args:
            config_manager: ConfigManager instance (provides all config + sub-managers)
            event_bus: EventBus for subscribing to hardware events

        Architecture:
            ConfigManager is the single source of truth for all configuration.
            DataAssembler loads state from state.json and builds domain objects.
            Services (ZoneService, AnimationService) manage runtime state with auto-save.
            EventBus provides event-driven hardware input handling.
        """

        # Store event bus
        self.event_bus = event_bus

        # Get ConfigManager and submanagers from it (dependency injection)
        self.config_manager: ConfigManager = config_manager
        self.color_manager: ColorManager = config_manager.color_manager # pyright: ignore[reportAttributeAccessIssue]
        self.animation_manager: AnimationManager = config_manager.animation_manager # pyright: ignore[reportAttributeAccessIssue]
        self.parameter_manager: ParameterManager = config_manager.parameter_manager # pyright: ignore[reportAttributeAccessIssue]
        self.hardware_manager: HardwareManager = config_manager.hardware_manager # pyright: ignore[reportAttributeAccessIssue]

        # Initialize domain services (NEW ARCHITECTURE - source of truth for zone/animation state)
        # Path relative to project root (where main_asyncio.py runs from)
        # NOTE: state.json moved to src/state/ (not src/config/)
        state_path = Path(__file__).parent.parent / "state" / "state.json"
        assembler = DataAssembler(config_manager, state_path)
        self.zone_service = ZoneService(assembler)
        self.animation_service = AnimationService(assembler)
        
         # Load persisted state (zones, animations, UI session)
        state = assembler.load_state()

        # Initialize UI/session service early (so we have current_mode etc.)
        self.ui_session_service = UISessionService(assembler)
        ui_state = self.ui_session_service.get_state()

        # Core UI state
        self.main_mode: MainMode = ui_state.main_mode
        self.edit_mode: bool = ui_state.edit_mode
        self.lamp_white_mode: bool = ui_state.lamp_white_mode
        self.lamp_white_saved_state: Optional[Dict] = ui_state.lamp_white_saved_state
        self.current_param: ParamID = ui_state.current_param
        self.current_zone_index: int = ui_state.current_zone_index

        # Build parameter cycling lists from ParameterManager
        zone_params = self.parameter_manager.get_zone_parameters()
        self.static_params = [pid for pid in zone_params.keys() if pid != ParamID.ZONE_REVERSED]  # Exclude REVERSED for now

        anim_params = self.parameter_manager.get_animation_parameters()
        # Only use base animation params (SPEED, INTENSITY) for cycling
        self.animation_params = [pid for pid in anim_params.keys() if pid in [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]]

        # Get zones from ZoneService (domain objects are source of truth)
        zones = self.zone_service.get_enabled()
        self.zone_ids = [z.config.id for z in zones]  # List[ZoneID] for indexing
        zone_configs = [z.config for z in zones]  # List[ZoneConfig] for ZoneStrip constructor

        # Hardware setup via HardwareManager (dependency injection)
        if self.config_manager.hardware_manager is None:
            return

        self.hardware_manager = self.config_manager.hardware_manager


        preview_config = self.hardware_manager.get_led_strip("preview")
        assert preview_config is not None
        self.preview_panel = PreviewPanel(
            gpio=preview_config["gpio"],  # Separate GPIO for preview
            count=preview_config["count"],
            color_order=ws.WS2811_STRIP_GRB,  # Preview panel is GRB (CJMCU-2812-8)
            brightness=255  # Max hardware brightness (software handles brightness via RGB scaling)
        )
        self.preview_controller = PreviewController(self.preview_panel)

        strip_config = self.hardware_manager.get_led_strip("strip")
        assert strip_config is not None
        self.strip = ZoneStrip(
            gpio=strip_config["gpio"],  # Separate GPIO for strip
            pixel_count=self.zone_service.get_total_pixel_count(),  # Auto-calculated from zones.yaml
            zones=zone_configs,  # Use ZoneConfig objects from domain layer
            color_order=ws.WS2811_STRIP_BRG,  # Strip uses BRG
            brightness=255  # Max hardware brightness (software handles brightness via RGB scaling)
        )

        # UI state (not managed by services - local to controller)
        # Set preview_mode based on current mode and parameter
        self.preview_mode: PreviewMode
        if self.main_mode == MainMode.STATIC:
            if self.current_param == ParamID.ZONE_BRIGHTNESS:
                self.preview_mode = PreviewMode.BAR_INDICATOR
            else:
                self.preview_mode = PreviewMode.COLOR_DISPLAY
        else:  # ANIMATION mode
            self.preview_mode = PreviewMode.ANIMATION_PREVIEW

        # Zone selection (index into self.zone_ids) - validate bounds

        # Animation system
        self.animation_engine: AnimationEngine = AnimationEngine(self.strip, zones)

        # Animation list for selection (AnimationID enums)
        all_animations = self.animation_service.get_all()
        self.available_animation_ids: List[AnimationID] = [animation.config.id for animation in all_animations]

        # Initialize selected_animation_index from service
        self.selected_animation_index = 0
        current_animation = self.animation_service.get_current()
        if current_animation and current_animation.config.id in self.available_animation_ids:
            self.selected_animation_index = self.available_animation_ids.index(current_animation.config.id)

        # Pulsing task for edit mode indicator
        self.pulse_task = None  # asyncio.Task for pulsing animation
        self.pulse_active = False
        self.pulse_lock = asyncio.Lock()

        # Initialize with default colors
        self._initialize_zones()
        
        
        # Start pulsing ONLY if edit_mode is ON and in STATIC mode
        if self.edit_mode and self.main_mode == MainMode.STATIC:
            self._start_pulse()

        # Auto-start animation if we're in ANIMATION mode and animation is enabled
        if self.main_mode == MainMode.ANIMATION and current_animation and current_animation.state.enabled:
            asyncio.create_task(self.start_animation())

        # Register event handlers (event-driven architecture)
        self._register_event_handlers()


    def _initialize_zones(self):
        """Initialize zones - apply colors from services to hardware"""
        # Apply colors from ZoneService to hardware
        for zone_id in self.zone_ids:
            r, g, b = self.zone_service.get_rgb(zone_id)
            zone_id_str = zone_id.name.lower()
            self.strip.set_zone_color(zone_id_str, r, g, b)

        # Sync preview with current zone
        self._sync_preview()

    def _register_event_handlers(self):
        """
        Register event handlers with EventBus

        Maps hardware events to controller methods:
        - Encoder rotations → handle_selector_rotation / handle_modulator_rotation
        - Encoder clicks → handle_selector_click / handle_modulator_click
        - Button presses → toggle_edit_mode / quick_lamp_white / power_toggle / toggle_main_mode
        """

        # Selector encoder: rotation and click
        self.event_bus.subscribe(EventType.ENCODER_ROTATE, lambda e: self.handle_selector_rotation(cast(EncoderRotateEvent, e).delta), filter_fn=lambda e: e.source == EncoderSource.SELECTOR)
        self.event_bus.subscribe(EventType.ENCODER_CLICK, lambda e: self.handle_selector_click(), filter_fn=lambda e: e.source == EncoderSource.SELECTOR)

        # Modulator encoder: rotation and click
        self.event_bus.subscribe(EventType.ENCODER_ROTATE, lambda e: self.handle_modulator_rotation(cast(EncoderRotateEvent, e).delta), filter_fn=lambda e: e.source == EncoderSource.MODULATOR)
        self.event_bus.subscribe(EventType.ENCODER_CLICK, lambda e: self.handle_modulator_click(), filter_fn=lambda e: e.source == EncoderSource.MODULATOR)

        # Buttons
        self.event_bus.subscribe(EventType.BUTTON_PRESS, lambda e: self.toggle_edit_mode(), filter_fn=lambda e: e.source == ButtonID.BTN1)
        self.event_bus.subscribe(EventType.BUTTON_PRESS, lambda e: self.quick_lamp_white(), filter_fn=lambda e: e.source == ButtonID.BTN2)
        self.event_bus.subscribe(EventType.BUTTON_PRESS, lambda e: self.power_toggle(), filter_fn=lambda e: e.source == ButtonID.BTN3)
        self.event_bus.subscribe(EventType.BUTTON_PRESS, lambda e: self.toggle_main_mode(), filter_fn=lambda e: e.source == ButtonID.BTN4)


    def _sync_preview(self):
        """
        Sync preview panel based on current mode and preview_mode

        Delegates to PreviewController for rendering.
        """

        if self.preview_mode == PreviewMode.COLOR_DISPLAY:
            zone_id = self._get_current_zone_id()
            zone = self.zone_service.get_zone(zone_id)
            rgb = zone.state.color.to_rgb()
            brightness = zone.brightness
            self.preview_controller.show_color(rgb, brightness)

        elif self.preview_mode == PreviewMode.BAR_INDICATOR:
            self._sync_preview_bar()

        elif self.preview_mode == PreviewMode.ANIMATION_PREVIEW:
            # Start animation preview based on selected animation with all parameters
            current_anim = self.animation_service.get_current()
            if current_anim:
                # Build parameter dict with all animation parameters
                params = {}
                for param_id in current_anim.parameters.keys():
                    value = current_anim.get_param_value(param_id)

                    # Map ParamID to preview parameter names
                    if param_id == ParamID.ANIM_SPEED:
                        params['speed'] = value
                    elif param_id == ParamID.ANIM_INTENSITY:
                        params['intensity'] = value
                    elif param_id == ParamID.ANIM_PRIMARY_COLOR_HUE:
                        params['hue'] = value
                    elif param_id == ParamID.ANIM_LENGTH:
                        params['length'] = value
                    elif param_id == ParamID.ANIM_HUE_OFFSET:
                        params['hue_offset'] = value

                # Extract speed separately (required positional arg)
                speed = params.pop('speed', 50)

                self.preview_controller.start_animation_preview(
                    current_anim.config.tag,
                    speed=speed,
                    **params
                )

    def _sync_preview_bar(self):
        """Sync preview bar indicator based on current parameter"""
        zone_id = self._get_current_zone_id()
        zone = self.zone_service.get_zone(zone_id)
        value = None
        max_value = 100
        base_color = (255, 255, 255)

        if self.main_mode == MainMode.STATIC and self.current_param == ParamID.ZONE_BRIGHTNESS:
            value = zone.brightness
            base_color = zone.state.color.to_rgb()

        elif self.main_mode == MainMode.ANIMATION:
            current_anim = self.animation_service.get_current()
            if current_anim:
                if self.current_param == ParamID.ANIM_SPEED:
                    value = current_anim.get_param_value(ParamID.ANIM_SPEED)
                elif self.current_param == ParamID.ANIM_INTENSITY and ParamID.ANIM_INTENSITY in current_anim.parameters:
                    value = current_anim.get_param_value(ParamID.ANIM_INTENSITY)

        # Show bar or fallback to color display
        if value is not None:
            self.preview_controller.show_bar(value, max_value, base_color)
        else:
            rgb = zone.state.color.to_rgb()
            brightness = zone.brightness
            self.preview_controller.show_color(rgb, brightness)
        
        
        
    def _get_current_zone_id(self) -> ZoneID:
        """Get currently selected zone ID (ZoneID enum)"""
        return self.zone_ids[self.current_zone_index]

    @property
    def current_animation_id(self) -> Optional[AnimationID]:
        """
        Get current animation ID from service (no caching)

        Returns:
            Current animation ID or None if no animation selected
        """
        current_anim = self.animation_service.get_current()
        return current_anim.config.id if current_anim else None

    def get_excluded_zone_ids(self) -> list[ZoneID]:
        """
        Get list of zone IDs to exclude from operations

        Centralized exclusion logic based on runtime state (lamp_white_mode).

        Returns:
            List of ZoneID enums to exclude (e.g., [ZoneID.LAMP])
        """
        excluded = []
        if self.lamp_white_mode:
            excluded.append(ZoneID.LAMP)
        return excluded

    def should_skip_zone(self, zone_id: ZoneID) -> bool:
        """
        Check if zone should be skipped for current operation

        Args:
            zone_id: ZoneID to check

        Returns:
            True if zone should be skipped
        """
        return zone_id in self.get_excluded_zone_ids()

    async def _pulse_zone_task(self):
        """Async pulsing animation for current zone - fixed 1s cycle"""
        cycle_duration = 1.0  # Fixed 1 second pulse cycle (independent from animation_speed)
        steps = 40

        while self.pulse_active:
            for step in range(steps):
                if not self.pulse_active:
                    break

                zone_id = self._get_current_zone_id()

                # Skip excluded zones (e.g., lamp in white mode)
                if self.should_skip_zone(zone_id):
                    await asyncio.sleep(cycle_duration / steps)
                    continue

                # Get zone from service
                zone = self.zone_service.get_zone(zone_id)

                # Get RGB from Color model (handles HUE/PRESET/WHITE)
                r, g, b = zone.state.color.to_rgb()
                base_brightness = zone.brightness

                # smooth sine pulse
                t = step / steps
                brightness_scale = 0.1 + 0.9 * (math.sin(t * 2 * math.pi - math.pi/2) + 1) / 2

                # Apply pulsing brightness
                pulsed_brightness = base_brightness * brightness_scale
                scale = pulsed_brightness / 100.0
                r, g, b = int(r * scale), int(g * scale), int(b * scale)

                # Convert ZoneID to tag for hardware compatibility
                zone_id_str = zone_id.name.lower()
                self.strip.set_zone_color(zone_id_str, r, g, b)
                await asyncio.sleep(cycle_duration / steps)
                
    def _start_pulse(self):
        """Launch async pulse"""
        if not self.pulse_active:
            self.pulse_active = True
            self.pulse_task = asyncio.create_task(self._pulse_zone_task())

    def _stop_pulse(self):
        """Stop async pulse and restore ALL zone colors"""
        self.pulse_active = False
        if self.pulse_task:
            self.pulse_task.cancel()

        # Restore ALL zones to their correct colors (not just current one)
        for zone_id in self.zone_ids:
            r, g, b = self.zone_service.get_rgb(zone_id)
            zone_id_str = zone_id.name.lower()
            self.strip.set_zone_color(zone_id_str, r, g, b)

    # ===== Public API =====
            
    def change_zone(self, delta):
        """
        Change selected zone

        Args:
            delta: -1 for previous, +1 for next
        """
        # IMPORTANT: Restore old zone to correct color BEFORE switching
        # Otherwise it stays at the pulsed brightness level
        old_zone_id = self._get_current_zone_id()
        r, g, b = self.zone_service.get_rgb(old_zone_id)
        old_zone_id_str = old_zone_id.name.lower()
        self.strip.set_zone_color(old_zone_id.name.lower(), r, g, b)

        # Now switch to new zone, skipping excluded zones
        for _ in range(len(self.zone_ids)):  # Max iterations to avoid infinite loop
            self.current_zone_index = (self.current_zone_index + delta) % len(self.zone_ids)
            zone_id = self._get_current_zone_id()

            # Skip excluded zones
            if self.should_skip_zone(zone_id):
                continue  # Try next zone
            else:
                break  # Found valid zone

        # Pulsing thread will automatically pick up the new zone (no restart needed)

        # Sync preview
        self._sync_preview()

        # Log zone change
        zone = self.zone_service.get_zone(zone_id)
        log.log(LogCategory.ZONE, "Zone changed",
                zone=zone.config.display_name,
                color=str(zone.state.color),
                brightness=f"{zone.brightness}%")

        self.ui_session_service.save(current_zone_index=self.current_zone_index)


    def toggle_edit_mode(self):
        """Toggle edit mode ON/OFF"""
        self.edit_mode = not self.edit_mode

        if self.edit_mode:
            if self.main_mode == MainMode.STATIC:
                zone_id = self._get_current_zone_id()
                zone = self.zone_service.get_zone(zone_id)
                log.log(LogCategory.SYSTEM, "Edit mode enabled",
                       mode=self.main_mode.name,
                       parameter=self.current_param.name,
                       zone=zone.config.display_name)
                self._start_pulse()
            else:
                log.log(LogCategory.SYSTEM, "Edit mode enabled",
                       mode=self.main_mode.name,
                       parameter=self.current_param.name,
                       animation=self.current_animation_id)
            self._sync_preview()
        else:
            log.log(LogCategory.SYSTEM, "Edit mode disabled")
            self._stop_pulse()

        self.ui_session_service.save(edit_mode=self.edit_mode)

    def quick_lamp_white(self):
        """
        Quick action: Toggle lamp white mode (BTN2)

        DESK LAMP MODE:
        - Lamp becomes independent desk lamp (warm white @ 100%)
        - Excluded from: zone selector, animations, pulsing, editing
        - Other zones work normally
        - Toggle again to restore previous state
        """
        lamp_zone = self.zone_service.get_zone(ZoneID.LAMP)

        if not self.lamp_white_mode:
            # ENTERING desk lamp mode
            # Save current state
            self.lamp_white_saved_state = {
                "color": lamp_zone.state.color.to_dict(),
                "brightness": lamp_zone.brightness
            }
            self.lamp_white_mode = True

            # If lamp is currently selected, switch to next zone
            if self._get_current_zone_id() == ZoneID.LAMP:
                self.change_zone(1)
                log.log(LogCategory.SYSTEM, "Auto-switched zone", reason="lamp_white_mode enabled")

            # Set to warm white using service
            warm_white = Color.from_preset("warm_white", self.color_manager)
            self.zone_service.set_color(ZoneID.LAMP, warm_white)
            self.zone_service.set_brightness(ZoneID.LAMP, 100)

            # Apply to hardware (Color model preserves exact RGB: 255, 200, 150)
            r, g, b = self.zone_service.get_rgb(ZoneID.LAMP)
            self.strip.set_zone_color("lamp", r, g, b)

            # Restart animation to exclude lamp
            if self.animation_engine.is_running():
                asyncio.create_task(self._restart_animation())

            log.log(LogCategory.SYSTEM, "Lamp white mode enabled",
                   mode="Desk Lamp",
                   excluded_from="zone selector, animations, pulsing")
        else:
            # EXITING desk lamp mode
            if self.lamp_white_saved_state:
                # Restore saved state using service
                saved_color = Color.from_dict(
                    self.lamp_white_saved_state["color"],
                    self.color_manager
                )
                saved_brightness = self.lamp_white_saved_state["brightness"]

                self.zone_service.set_color(ZoneID.LAMP, saved_color)
                self.zone_service.set_brightness(ZoneID.LAMP, saved_brightness)

                # Apply to hardware
                r, g, b = self.zone_service.get_rgb(ZoneID.LAMP)
                self.strip.set_zone_color("lamp", r, g, b)

                lamp_zone_updated = self.zone_service.get_zone(ZoneID.LAMP)
                log.log(LogCategory.SYSTEM, "Lamp white mode disabled",
                       lamp_color=str(lamp_zone_updated.state.color),
                       brightness=f"{lamp_zone_updated.brightness}%")

                self.lamp_white_saved_state = None

            self.lamp_white_mode = False

            # Restart animation to include lamp
            if self.animation_engine.is_running():
                asyncio.create_task(self._restart_animation())

        self.ui_session_service.save(
            lamp_white_mode=self.lamp_white_mode,
            lamp_white_saved_state=self.lamp_white_saved_state
        )

    def power_toggle(self):
        """Toggle power for all zones (ON/OFF) - saves and restores brightness and animation state"""
        # Schedule async power toggle task
        asyncio.create_task(self._power_toggle_async())

    async def _power_toggle_async(self):
        """Async implementation of power toggle with smooth transitions"""
        # Check if any zone has brightness > 0
        any_on = any(self.zone_service.get_zone(zone_id).brightness > 0 for zone_id in self.zone_ids)

        if any_on:
            # Turning OFF: Save current brightness and animation state, then fade out
            if not hasattr(self, 'power_saved_brightness'):
                self.power_saved_brightness = {}

            # Save brightness from service
            for zone_id in self.zone_ids:
                zone = self.zone_service.get_zone(zone_id)
                self.power_saved_brightness[zone_id] = zone.brightness

            # Save animation state and stop it with transition
            self.power_saved_animation_enabled = self.animation_engine.is_running()
            if self.animation_engine.is_running():
                # Use POWER_TOGGLE transition for smooth fade
                transition = self.animation_engine.transition_service.POWER_TOGGLE
                await self.animation_engine.stop(transition)
            else:
                # No animation running - apply fade-out transition to static state
                transition = self.strip.transition_service.POWER_TOGGLE
                await self.strip.transition_service.fade_out(transition)

            # Turn off all zones (state only, transition already rendered fade)
            for zone_id in self.zone_ids:
                self.zone_service.set_brightness(zone_id, 0)

            self.preview_panel.clear()
            log.log(LogCategory.SYSTEM, "Power OFF", saved="brightness and animation state")
        else:
            # Turning ON: Restore saved brightness and animation state with fade-in
            # Build target frame without showing (to avoid flicker)
            target_colors = {}

            if hasattr(self, 'power_saved_brightness') and self.power_saved_brightness:
                # Restore saved brightness
                for zone_id in self.zone_ids:
                    saved = self.power_saved_brightness.get(zone_id, 64)
                    self.zone_service.set_brightness(zone_id, saved)

                    # Prepare target color (don't show yet)
                    r, g, b = self.zone_service.get_rgb(zone_id)
                    zone_id_str = zone_id.name.lower()
                    target_colors[zone_id_str] = (r, g, b)
                log.log(LogCategory.SYSTEM, "Power ON", restored="saved brightness")
            else:
                # No saved state, use default brightness (50%)
                for zone_id in self.zone_ids:
                    self.zone_service.set_brightness(zone_id, 50)

                    # Prepare target color (don't show yet)
                    r, g, b = self.zone_service.get_rgb(zone_id)
                    zone_id_str = zone_id.name.lower()
                    target_colors[zone_id_str] = (r, g, b)
                log.log(LogCategory.SYSTEM, "Power ON", brightness="default 50%")

            # Build target frame for fade-in (zone colors → pixel frame)
            target_frame = self.strip.build_frame_from_zones(target_colors)

            # Apply fade-in transition (from black to target)
            transition = self.strip.transition_service.POWER_TOGGLE
            await self.strip.transition_service.fade_in(target_frame, transition)

            # Restore animation if it was running
            if hasattr(self, 'power_saved_animation_enabled') and self.power_saved_animation_enabled:
                await self.start_animation()
                log.log(LogCategory.ANIMATION, "Animation restarted after power ON")

            self._sync_preview()

    def clear_all(self):
        """Turn off all LEDs"""
        self.strip.clear()
        self.preview_panel.clear()
        log.log(LogCategory.SYSTEM, "All LEDs cleared")

    def _build_animation_params(self) -> Dict:
        """
        Build animation-specific parameters using domain model

        Delegates to AnimationCombined.build_params_for_engine() to avoid duplication.

        Returns:
            Dict of animation parameters
        """
        current_animation = self.animation_service.get_current()
        if not current_animation:
            return {"speed": 50}

        # Get current zone for reference (used by build_params_for_engine)
        current_zone_id = self._get_current_zone_id()
        current_zone = self.zone_service.get_zone(current_zone_id)

        # Use domain model method (single source of truth)
        return current_animation.build_params_for_engine(current_zone)

    def _cache_zone_colors(self):
        """Cache current zone colors with brightness for breathe animation"""
        if not self.animation_engine.current_animation:
            return

        for zone_id in self.zone_ids:
            # Get color with brightness already applied from service
            zone_red, zone_green, zone_blue = self.zone_service.get_rgb(zone_id)
            zone_id_str = zone_id.name.lower()
            self.animation_engine.current_animation.set_zone_color_cache(zone_id_str, zone_red, zone_green, zone_blue)

    async def start_animation(self):
        """Start the currently selected animation"""
        if self.animation_engine.is_running():
            log.log(LogCategory.ANIMATION, "Animation already running", level=LogLevel.INFO)
            return

        # Stop pulsing if active
        if self.edit_mode and self.pulse_active:
            self._stop_pulse()

        # Build parameters (with brightness already applied) and start animation
        animation_params = self._build_animation_params()
        excluded_zone_ids = self.get_excluded_zone_ids()
        excluded_zone_tags = [zone_id.name.lower() for zone_id in excluded_zone_ids]

        # Convert AnimationID enum to tag string for animation engine
        anim_id = self.current_animation_id
        if not anim_id:
            log.log(LogCategory.ANIMATION, "No animation selected", level=LogLevel.ERROR)
            return

        animation_tag = anim_id.name.lower()
        
        # Stop current animation with fade transition if running
        if self.animation_engine.is_running():
            from models.transition import TransitionConfig
            transition = self.animation_engine.transition_service.ANIMATION_SWITCH
            await self.animation_engine.stop(transition)
        
        await self.animation_engine.start(animation_tag, excluded_zones=excluded_zone_tags, **animation_params)

        # Cache zone colors for breathe animation (per-zone colors)
        if anim_id == AnimationID.BREATHE:
            self._cache_zone_colors()

        current_animation = self.animation_service.get_current()
        if current_animation:
            animation_speed = current_animation.get_param_value(ParamID.ANIM_SPEED)
            log.log(LogCategory.ANIMATION, "Animation started",
                   id=current_animation.config.display_name,
                   speed=f"{animation_speed}/100")

    async def stop(self, clear_on_stop: bool = True):
        """Stop current animation and restore static colors"""
        if not self.animation_engine.is_running():
            return

        await self.animation_engine.stop()

        if clear_on_stop:
            # Restore all zones to their static colors from service
            for zone_id in self.zone_ids:
                zone_red, zone_green, zone_blue = self.zone_service.get_rgb(zone_id)
                zone_id_str = zone_id.name.lower()
                self.strip.set_zone_color(zone_id_str, zone_red, zone_green, zone_blue)

        # Restart pulsing if edit mode is on
        if self.edit_mode:
            self._start_pulse()

        log.log(LogCategory.ANIMATION, "Animation stopped")

    async def _restart_animation(self):
        """Restart animation (stop then start with new animation_id)"""
        log.debug(LogCategory.ANIMATION, "RESTARTING ANIMATION")
        from models.transition import TransitionConfig
        # Use a longer fade for restart (900ms)
        transition = TransitionConfig(duration_ms=900, steps=20)
        await self.animation_engine.stop(transition)
        await self.start_animation()

    def select_animation(self, delta):
        """
        Select animation (cycle through available animations)

        Automatically restarts animation if one is currently running.

        Args:
            delta: -1 for previous, +1 for next
        """
        was_running = self.animation_engine.is_running()

        log.debug(LogCategory.ANIMATION, f"Cycle index={self.selected_animation_index}, list={self.available_animation_ids}")
        
        # Cycle through available animation IDs
        self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animation_ids)
        new_animation_id = self.available_animation_ids[self.selected_animation_index]

        # Update service to reflect new selection
        self.animation_service.set_current(new_animation_id)

        selected_animation = self.animation_service.get_animation(new_animation_id)
        log.animation(
            "Animation selected",
            id=selected_animation.config.display_name,
            index=f"{self.selected_animation_index + 1}/{len(self.available_animation_ids)}"
        )

        # Update preview first (before restarting animation)
        self._sync_preview()

        # Restart animation if it was running
        if was_running:
            asyncio.create_task(self._restart_animation())

    # ===== Two-Mode System (STATIC vs ANIMATION) =====

    def _switch_to_animation_mode(self):
        """Switch from STATIC to ANIMATION mode"""
        self.main_mode = MainMode.ANIMATION

        # Stop pulsing (animation mode doesn't pulse zones)
        if self.pulse_active:
            self._stop_pulse()

        # Set preview to animation preview
        self.preview_mode = PreviewMode.ANIMATION_PREVIEW
        self._sync_preview()

        # Switch current param to first animation param
        self.current_param = self.animation_params[0]

        # Auto-start animation if not already running
        if not self.animation_engine.is_running():
            asyncio.create_task(self.start_animation())

        # asyncio.create_task(self.preview_ctrl.start_animation_preview(
        #     self.animation_engine.get_preview_generator("snake"),
        #     speed=self.animation_speed
        # ))
                
        # Log with parameter-specific details
        current_animation = self.animation_service.get_current()
        log_kwargs = {"animation_id": current_animation.config.display_name if current_animation else "None",
                     "parameter": self.current_param.name}
        if current_animation:
            if self.current_param == ParamID.ANIM_SPEED:
                animation_speed = current_animation.get_param_value(ParamID.ANIM_SPEED)
                log_kwargs["speed"] = f"{animation_speed}/100"
            elif self.current_param == ParamID.ANIM_INTENSITY and ParamID.ANIM_INTENSITY in current_animation.parameters:
                animation_intensity = current_animation.get_param_value(ParamID.ANIM_INTENSITY)
                log_kwargs["intensity"] = f"{animation_intensity}/100"
        log.info(LogCategory.SYSTEM, "Mode switched to ANIMATION", **log_kwargs)

    def _switch_to_static_mode(self):
        """Switch from ANIMATION to STATIC mode"""
        self.main_mode = MainMode.STATIC

        # Switch current param to first static param
        self.current_param = self.static_params[0]

        # Stop animation if running
        if self.animation_engine.is_running():
            from models.transition import TransitionConfig
            transition = self.animation_engine.transition_service.MODE_SWITCH
            asyncio.create_task(self.animation_engine.stop(transition))

        # Restore static zone colors to hardware
        self._initialize_zones()

        # Restart pulsing if edit_mode=ON
        if self.edit_mode:
            self._start_pulse()

        # Set preview based on current parameter
        if self.current_param == ParamID.ZONE_BRIGHTNESS:
            self.preview_mode = PreviewMode.BAR_INDICATOR
        else:
            self.preview_mode = PreviewMode.COLOR_DISPLAY
        self._sync_preview()

        # Log with parameter-specific details
        current_zone_id = self._get_current_zone_id()
        current_zone = self.zone_service.get_zone(current_zone_id)
        log_kwargs = {"zone": current_zone.config.display_name, "parameter": self.current_param.name}
        if self.current_param == ParamID.ZONE_COLOR_HUE:
            log_kwargs["hue"] = f"{current_zone.state.color.to_hue()}°"
        elif self.current_param == ParamID.ZONE_COLOR_PRESET:
            log_kwargs["preset"] = str(current_zone.state.color)
        elif self.current_param == ParamID.ZONE_BRIGHTNESS:
            log_kwargs["brightness"] = f"{current_zone.brightness}%"
        log.info(LogCategory.SYSTEM, "Mode switched to STATIC", **log_kwargs)

    def toggle_main_mode(self):
        """
        Toggle between STATIC and ANIMATION mode (BTN4)

        STATIC → ANIMATION:
          - Stop pulsing
          - Keep current zone selected (for reference)
          - Switch to animation parameter selection

        ANIMATION → STATIC:
          - Restart pulsing if edit_mode=ON
          - Return to zone editing
        """
        if self.main_mode == MainMode.STATIC:
            self._switch_to_animation_mode()
        else:
            self._switch_to_static_mode()

        self.ui_session_service.save(
            main_mode=self.main_mode,
            current_param=self.current_param
        )

    def handle_selector_rotation(self, delta: int):
        """
        Handle selector encoder ROTATION (context-sensitive)

        STATIC mode: Change zone
        ANIMATION mode: Select animation

        Args:
            delta: Rotation direction (-1 or +1)
        """
        if self.main_mode == MainMode.STATIC:
            self.change_zone(delta)
        else:  # ANIMATION mode
            self.select_animation(delta)

    def handle_selector_click(self):
        """
        Handle selector encoder CLICK (context-sensitive)

        STATIC mode: (unused)
        ANIMATION mode: Start/Stop animation
        """
        if not self.edit_mode:
            log.log(LogCategory.SYSTEM, "Edit mode required", level=LogLevel.INFO, action="Press BTN1 to enter edit mode")
            return

        if self.main_mode == MainMode.STATIC:
            # Unused in STATIC mode
            log.log(LogCategory.SYSTEM, "Selector click unused in STATIC mode", level=LogLevel.INFO, tip="Use modulator click to cycle parameters")
            return

        # ANIMATION mode: Toggle animation ON/OFF
        if self.animation_engine.is_running():
            from models.transition import TransitionConfig
            transition = self.animation_engine.transition_service.ANIMATION_SWITCH
            asyncio.create_task(self.animation_engine.stop(transition))
        else:
            asyncio.create_task(self.start_animation())

    def _adjust_zone_parameter(self, zone_id: ZoneID, delta: int):
        """
        Adjust zone-specific parameter (hue, preset, brightness)

        NOTE: Color adjustments (HUE/PRESET) are NOT parameters - they're Color object operations.
        Only BRIGHTNESS is a true parameter in the domain model.

        Args:
            zone_id: ZoneID to adjust
            delta: Rotation direction (-1 or +1)
        """
        zone = self.zone_service.get_zone(zone_id)

        if self.current_param == ParamID.ZONE_COLOR_HUE:
            # Adjust hue - Color operation, not parameter
            new_color = zone.state.color.adjust_hue(delta * 10)
            self.zone_service.set_color(zone_id, new_color)

            hue = new_color.to_hue()
            r, g, b = new_color.to_rgb()
            log.zone("Zone hue adjusted",
                    zone=zone.config.display_name,
                    hue=f"{hue}°",
                    rgb=f"({r},{g},{b})")
            self._sync_preview()

        elif self.current_param == ParamID.ZONE_COLOR_PRESET:
            # Cycle presets - Color operation, not parameter
            new_color = zone.state.color.next_preset(delta, self.color_manager)
            self.zone_service.set_color(zone_id, new_color)

            log.log(LogCategory.ZONE, "Preset changed",
                   zone=zone.config.display_name,
                   preset=str(new_color))
            self._sync_preview()

        elif self.current_param == ParamID.ZONE_BRIGHTNESS:
            # Brightness IS a parameter - delegate to service's adjust_parameter
            self.zone_service.adjust_parameter(zone_id, ParamID.ZONE_BRIGHTNESS, delta)

            # Apply updated brightness to hardware
            r, g, b = self.zone_service.get_rgb(zone_id)
            zone_id_str = zone_id.name.lower()
            self.strip.set_zone_color(zone_id_str, r, g, b)

            # Log and sync preview
            zone_updated = self.zone_service.get_zone(zone_id)
            log.log(LogCategory.ZONE, "Brightness adjusted",
                   zone=zone_updated.config.display_name,
                   brightness=f"{zone_updated.brightness}%")
            self._sync_preview()

    def _adjust_animation_parameter(self, delta: int):
        """
        Adjust animation-specific parameter (speed, intensity)

        Args:
            delta: Rotation direction (-1 or +1)
        """
        current_anim = self.animation_service.get_current()
        if not current_anim:
            return

        if self.current_param == ParamID.ANIM_SPEED:
            # Adjust speed via service
            self.animation_service.adjust_parameter(current_anim.config.id, ParamID.ANIM_SPEED, delta)

            anim_updated = self.animation_service.get_animation(current_anim.config.id)
            new_speed = anim_updated.get_param_value(ParamID.ANIM_SPEED)

            if self.animation_engine.is_running():
                self.animation_engine.update_param("speed", new_speed)

            log.log(LogCategory.ANIMATION, "Speed adjusted", speed=f"{new_speed}/100")
            self._sync_preview()

        elif self.current_param == ParamID.ANIM_INTENSITY:
            # Check if current animation has intensity parameter
            if ParamID.ANIM_INTENSITY not in current_anim.parameters:
                log.log(LogCategory.ANIMATION, "Animation doesn't support intensity parameter",
                       animation=current_anim.config.display_name, level=LogLevel.WARN)
                return

            # Adjust intensity via service
            self.animation_service.adjust_parameter(current_anim.config.id, ParamID.ANIM_INTENSITY, delta)

            anim_updated = self.animation_service.get_animation(current_anim.config.id)
            new_intensity = anim_updated.get_param_value(ParamID.ANIM_INTENSITY)

            if self.animation_engine.is_running():
                self.animation_engine.update_param("intensity", new_intensity)

            log.log(LogCategory.ANIMATION, "Intensity adjusted", intensity=f"{new_intensity}/100")
            self._sync_preview()

        else:
            # Generic parameter adjustment for other animation params (length, hue, hue_offset, etc.)
            if self.current_param not in current_anim.parameters:
                log.log(LogCategory.ANIMATION, "Parameter not available for current animation",
                       parameter=self.current_param.name,
                       animation=current_anim.config.display_name, level=LogLevel.WARN)
                return

            # Adjust via service
            self.animation_service.adjust_parameter(current_anim.config.id, self.current_param, delta)

            anim_updated = self.animation_service.get_animation(current_anim.config.id)
            new_value = anim_updated.get_param_value(self.current_param)

            # Map ParamID to animation parameter name for update_param
            param_name_map = {
                ParamID.ANIM_LENGTH: "length",
                ParamID.ANIM_HUE_OFFSET: "hue_offset",
                ParamID.ANIM_PRIMARY_COLOR_HUE: "hue",
            }

            if self.current_param in param_name_map and self.animation_engine.is_running():
                param_name = param_name_map[self.current_param]
                self.animation_engine.update_param(param_name, new_value)

            log.log(LogCategory.ANIMATION, f"{self.current_param.name} adjusted",
                   parameter=self.current_param.name,
                   value=new_value)
            self._sync_preview()

    def handle_modulator_rotation(self, delta: int):
        """
        Handle modulator encoder ROTATION (context-sensitive)

        STATIC mode: Adjust parameter value (color, brightness)
        ANIMATION mode: Adjust parameter value (speed, intensity)

        Args:
            delta: Rotation direction (-1 or +1)
        """
        if not self.edit_mode:
            return

        if self.main_mode == MainMode.STATIC:
            zone_id = self._get_current_zone_id()

            # Block editing excluded zones
            if self.should_skip_zone(zone_id):
                zone = self.zone_service.get_zone(zone_id)
                log.log(LogCategory.SYSTEM, "Zone is excluded from editing",
                       zone=zone.config.display_name,
                       reason="lamp_white_mode")
                return

            self._adjust_zone_parameter(zone_id, delta)
        else:
            self._adjust_animation_parameter(delta)

    def handle_modulator_click(self):
        """
        Handle modulator encoder CLICK (context-sensitive)

        Both modes: Cycle parameters
        """
        if not self.edit_mode:
            log.log(LogCategory.SYSTEM, "Edit mode required", level=LogLevel.INFO, action="Press BTN1 to enter edit mode")
            return

        # Get appropriate cycling list based on mode
        if self.main_mode == MainMode.STATIC:
            params = self.static_params
        else:  # ANIMATION mode - use current animation's parameters
            current_anim = self.animation_service.get_current()
            if current_anim:
                params = list(current_anim.parameters.keys())
            else:
                params = [ParamID.ANIM_SPEED]  # Fallback

        # Cycle to next parameter
        if self.current_param in params:
            idx = params.index(self.current_param)
            self.current_param = params[(idx + 1) % len(params)]
        else:
            # Current param not in list, use first available
            self.current_param = params[0]

        # Update preview mode based on current mode and parameter
        if self.main_mode == MainMode.STATIC:
            if self.current_param == ParamID.ZONE_BRIGHTNESS:
                self.preview_mode = PreviewMode.BAR_INDICATOR
            elif self.current_param in (ParamID.ZONE_COLOR_HUE, ParamID.ZONE_COLOR_PRESET):
                self.preview_mode = PreviewMode.COLOR_DISPLAY
        else:  # ANIMATION mode
            # In animation mode, preview is always animation preview regardless of which parameter is active
            self.preview_mode = PreviewMode.ANIMATION_PREVIEW

        self._sync_preview()

        # Log parameter switch with current value
        if self.main_mode == MainMode.STATIC:
            zone_id = self._get_current_zone_id()
            zone = self.zone_service.get_zone(zone_id)
            value_str = ""
            if self.current_param == ParamID.ZONE_COLOR_HUE:
                value_str = f"{zone.state.color.to_hue()}°"
            elif self.current_param == ParamID.ZONE_COLOR_PRESET:
                value_str = str(zone.state.color)
            elif self.current_param == ParamID.ZONE_BRIGHTNESS:
                value_str = f"{zone.brightness}%"
            log.info(LogCategory.SYSTEM, f"Param cycled: {self.current_param.name} | {zone.config.display_name}: {value_str}")
        else:  # ANIMATION mode
            current_anim = self.animation_service.get_current()
            value_str = ""
            if current_anim:
                if self.current_param == ParamID.ANIM_SPEED:
                    value_str = f"{current_anim.get_param_value(ParamID.ANIM_SPEED)}/100"
                elif self.current_param == ParamID.ANIM_INTENSITY:
                    # Check if animation has ANIM_INTENSITY (not all do!)
                    if ParamID.ANIM_INTENSITY in current_anim.parameters:
                        value_str = f"{current_anim.get_param_value(ParamID.ANIM_INTENSITY)}/100"
            log.info(LogCategory.SYSTEM, f"Param cycled: {self.current_param.name} = {value_str}")
        
        self.ui_session_service.save(current_param=self.current_param)
        
    def get_status(self):
        """
        Get current UI state (NOT zone/animation data - services handle that)

        This only returns UI-specific state that's not managed by services:
        - edit_mode, lamp_white_mode (UI toggles)
        - current_zone_index, main_mode, current_param (UI navigation)

        Zone/animation data is persisted automatically by services.

        Returns:
            Dict with UI state only
        """
        return {
            "main_mode": self.main_mode.name,
            "current_param": self.current_param.name,
            "current_zone_index": self.current_zone_index,
            "edit_mode": self.edit_mode,
            "lamp_white_mode": self.lamp_white_mode,
            "lamp_white_saved_state": self.lamp_white_saved_state
        }

