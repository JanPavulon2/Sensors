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
from rpi_ws281x import ws, Color as RGBColor  # Rename to avoid conflict with models.Color
from components import PreviewPanel, ZoneStrip, PreviewController
from utils.logger import get_logger, LogLevel, LogCategory
from animations import AnimationEngine
from models import Color, ColorMode, MainMode, PreviewMode, ParamID
from managers import ConfigManager, ColorManager, AnimationManager, ParameterManager, HardwareManager

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


    def __init__(self, config_manager: ConfigManager, state: Dict):
        """
        Initialize LED Controller

        Args:
            config_manager: ConfigManager instance (provides all config + sub-managers)
            state: State dict loaded from state.json

        Architecture:
            ConfigManager is the single source of truth for all configuration.
            LEDController receives managers via dependency injection.
        """
        self.state: Dict = state
        
        # Get ConfigManager and submanagers from it (dependency injection)
        self.config_manager: ConfigManager = config_manager
        self.color_manager: ColorManager = config_manager.color_manager # pyright: ignore[reportAttributeAccessIssue]
        self.animation_manager: AnimationManager = config_manager.animation_manager # pyright: ignore[reportAttributeAccessIssue]
        self.parameter_manager: ParameterManager = config_manager.parameter_manager # pyright: ignore[reportAttributeAccessIssue]
        self.hardware_manager: HardwareManager = config_manager.hardware_manager # pyright: ignore[reportAttributeAccessIssue]
        
        # Build parameter cycling lists from ParameterManager
        zone_params = self.parameter_manager.get_zone_parameters()
        self.static_params = [pid for pid in zone_params.keys() if pid != ParamID.ZONE_REVERSED]  # Exclude REVERSED for now

        anim_params = self.parameter_manager.get_animation_parameters()
        # Only use base animation params (SPEED, INTENSITY) for cycling
        self.animation_params = [pid for pid in anim_params.keys() if pid in [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]]

        # Get zones from ConfigManager
        zones = config_manager.get_enabled_zones()  # List[Zone]
        self.zones = zones  # Store Zone objects for future use
        self.zone_names = [zone.tag for zone in zones]

        # Hardware setup via HardwareManager (dependency injection)
        hardware_manager = config_manager.hardware_manager

        preview_config = hardware_manager.get_led_strip("preview")
        self.preview_panel = PreviewPanel(
            gpio=preview_config["gpio"],  # Separate GPIO for preview
            count=preview_config["count"],
            color_order=ws.WS2811_STRIP_GRB,  # Preview panel is GRB (CJMCU-2812-8)
            brightness=255  # Max hardware brightness (software handles brightness via RGB scaling)
        )
        self.preview_controller = PreviewController(self.preview_panel)

        strip_config = hardware_manager.get_led_strip("strip")
        self.strip = ZoneStrip(
            gpio=strip_config["gpio"],  # Separate GPIO for strip
            pixel_count=strip_config["count"],  # Total: 99 physical LEDs / 3 = 33 pixels
            zones=zones,
            color_order=ws.WS2811_STRIP_BRG,  # Strip uses BRG
            brightness=255  # Max hardware brightness (software handles brightness via RGB scaling)
        )

        # Global state
        self.edit_mode: bool = state.get("edit_mode", True)

        # Lamp white mode (desk lamp mode - lamp excluded from everything)
        self.lamp_white_mode: bool = state.get("lamp_white_mode", False)
        self.lamp_white_saved_state: Optional[Dict] = state.get("lamp_white_saved_state", None)

        # Two-mode system (STATIC vs ANIMATION) - load from state
        try:
            self.main_mode: MainMode = MainMode[state.get("main_mode", "STATIC")]
        except KeyError:
            self.main_mode = MainMode.STATIC

        # Current parameter (using ParamID)
        try:
            self.current_param: ParamID = ParamID[state.get("current_param", "ZONE_COLOR_HUE")]
        except KeyError:
            self.current_param = ParamID.ZONE_COLOR_HUE

        # Set preview_mode based on current mode and parameter
        self.preview_mode: PreviewMode
        if self.main_mode == MainMode.STATIC:
            if self.current_param == ParamID.ZONE_BRIGHTNESS:
                self.preview_mode = PreviewMode.BAR_INDICATOR
            else:
                self.preview_mode = PreviewMode.COLOR_DISPLAY
        else:  # ANIMATION mode
            self.preview_mode = PreviewMode.ANIMATION_PREVIEW

        # Zone selection
        self.current_zone_index: int = state.get("current_zone_index", 0)

        # Parameters per zone (using Color model - SINGLE SOURCE OF TRUTH)
        self.zone_colors: Dict[str, Color] = {}
        self.zone_brightness: Dict[str, int] = {}  # 0-100%

        for zone_name in self.zone_names:
            zone_state = state["zones"][zone_name]

            # Migrate color from old format (hue, preset) to new format (Color class)
            if "color" in zone_state and isinstance(zone_state["color"], dict):
                # New format: Color.to_dict()
                self.zone_colors[zone_name] = Color.from_dict(zone_state["color"], self.color_manager)
            else:
                # Old format: hue + preset (use hue as source of truth)
                hue = zone_state.get("hue", 0)
                self.zone_colors[zone_name] = Color.from_hue(hue)

            # Load brightness (0-100%)
            self.zone_brightness[zone_name] = zone_state.get("brightness", 100)

        # Animation system
        self.animation_engine: AnimationEngine = AnimationEngine(self.strip, zones)

        # Animation state
        anim_state = state.get("animation", {})
        self._animation_should_run: bool = anim_state.get("enabled", False)
        self.animation_id: str = anim_state.get("id", "breathe")
        self.animation_speed: int = anim_state.get("speed", 50)
        self.animation_color: Optional[tuple] = anim_state.get("color", None)
        self.animation_color2: Optional[tuple] = anim_state.get("color2", None)
        self.animation_intensity: int = anim_state.get("intensity", 100)

        # Animation list for selection (from AnimationManager)
        self.available_animations = self.animation_manager.get_animation_ids()
        self.selected_animation_index = 0
        if self.animation_id in self.available_animations:
            self.selected_animation_index = self.available_animations.index(self.animation_id)

        # Pulsing task for edit mode indicator
        self.pulse_task = None  # asyncio.Task for pulsing animation
        self.pulse_active = False
        self.pulse_lock = asyncio.Lock()

        # Initialize with default colors
        self._initialize_zones()

        # Start pulsing ONLY if edit_mode is ON and in STATIC mode
        if self.edit_mode and self.main_mode == MainMode.STATIC:
            self._start_pulse()

        # Auto-start animation if we're in ANIMATION mode and animation should run
        if self.main_mode == MainMode.ANIMATION and self._animation_should_run:
            asyncio.create_task(self.start_animation())


    def _initialize_zones(self):
        """Initialize zones - apply colors from loaded state"""
        # Apply colors from state to hardware
        for zone_name in self.zone_names:
            r, g, b = self._get_zone_color(zone_name)
            self.strip.set_zone_color(zone_name, r, g, b)

        # self.preview_controller
        # Sync preview with current zone
        self._sync_preview()

    def _sync_preview(self):
        """
        Sync preview panel based on current mode and preview_mode

        Delegates to PreviewController for rendering.
        """

        if self.preview_mode == PreviewMode.COLOR_DISPLAY:
            zone_tag = self._get_current_zone()
            rgb = self.zone_colors[zone_tag].to_rgb()
            brightness = self.zone_brightness[zone_tag]
            self.preview_controller.show_color(rgb, brightness)

        elif self.preview_mode == PreviewMode.BAR_INDICATOR:
            self._sync_preview_bar()

        elif self.preview_mode == PreviewMode.ANIMATION_PREVIEW:
            # Start animation preview based on selected animation
            self.preview_controller.start_animation_preview(
                self.animation_id,
                speed=self.animation_speed
            )
    
    def _sync_preview_bar(self):
        """Sync preview bar indicator based on current parameter"""
        zone_tag = self._get_current_zone()
        value = None
        max_value = 100
        base_color = (255, 255, 255)

        if self.main_mode == MainMode.STATIC and self.current_param == ParamID.ZONE_BRIGHTNESS:
            value = self.zone_brightness[zone_tag]
            base_color = self.zone_colors[zone_tag].to_rgb()

        elif self.main_mode == MainMode.ANIMATION:
            if self.current_param == ParamID.ANIM_SPEED:
                value = self.animation_speed
            elif self.current_param == ParamID.ANIM_INTENSITY:
                value = self.animation_intensity

        # Show bar or fallback to color display
        if value is not None:
            self.preview_controller.show_bar(value, max_value, base_color)
        else:
            rgb = self.zone_colors[zone_tag].to_rgb()
            brightness = self.zone_brightness[zone_tag]
            self.preview_controller.show_color(rgb, brightness)
        
        
        
    def _get_zone_color(self, zone_name):
        """
        Get current RGB color for a zone with brightness applied

        NEW: Uses Color class which properly handles white presets.

        Returns:
            (r, g, b) tuple with brightness applied
        """
        # Get base color from Color class (handles HUE/PRESET/RGB modes)
        color = self.zone_colors[zone_name]
        r, g, b = color.to_rgb()

        # Apply brightness (0-100%)
        brightness = self.zone_brightness[zone_name]
        scale = brightness / 100.0
        return int(r * scale), int(g * scale), int(b * scale)

    def _get_current_zone(self):
        """Get current zone tag (str)"""
        return self.zone_names[self.current_zone_index]

    def _get_zone_by_tag(self, tag: str):
        """
        Get Zone object by tag

        Args:
            tag: Zone tag (e.g., "lamp", "top")

        Returns:
            Zone object or None if not found
        """
        for zone in self.zones:
            if zone.tag == tag:
                return zone
        return None

    def get_excluded_zones(self) -> list:
        """
        Get list of zones to exclude from operations

        Centralized exclusion logic based on runtime state (lamp_white_mode).

        Returns:
            List of zone tags to exclude (e.g., ["lamp"])
        """
        excluded = []
        if self.lamp_white_mode:
            excluded.append("lamp")
        return excluded

    def should_skip_zone(self, zone_name: str) -> bool:
        """
        Check if zone should be skipped for current operation

        Args:
            zone_name: Zone tag to check

        Returns:
            True if zone should be skipped
        """
        return zone_name in self.get_excluded_zones()

    async def _pulse_zone_task(self):
        """Async pulsing animation for current zone - fixed 1s cycle"""
        cycle_duration = 1.0  # Fixed 1 second pulse cycle (independent from animation_speed)
        steps = 40

        while self.pulse_active:
            for step in range(steps):
                if not self.pulse_active:
                    break

                zone_name = self._get_current_zone()

                # Skip excluded zones (e.g., lamp in white mode)
                if self.should_skip_zone(zone_name):
                    await asyncio.sleep(cycle_duration / steps)
                    continue

                # Get RGB from Color model (handles HUE/PRESET/WHITE)
                r, g, b = self.zone_colors[zone_name].to_rgb()

                base_brightness = self.zone_brightness[zone_name]

                # smooth sine pulse
                t = step / steps
                brightness_scale = 0.1 + 0.9 * (math.sin(t * 2 * math.pi - math.pi/2) + 1) / 2

                # Apply pulsing brightness
                pulsed_brightness = base_brightness * brightness_scale
                scale = pulsed_brightness / 100.0  # Changed from /255 to /100
                r, g, b = int(r * scale), int(g * scale), int(b * scale)

                self.strip.set_zone_color(zone_name, r, g, b)
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
        for zone_name in self.zone_names:
            r, g, b = self._get_zone_color(zone_name)
            self.strip.set_zone_color(zone_name, r, g, b)

    # ===== Public API =====
            
    def change_zone(self, delta):
        """
        Change selected zone

        Args:
            delta: -1 for previous, +1 for next
        """
        # IMPORTANT: Restore old zone to correct color BEFORE switching
        # Otherwise it stays at the pulsed brightness level
        old_zone_name = self._get_current_zone()
        r, g, b = self._get_zone_color(old_zone_name)
        self.strip.set_zone_color(old_zone_name, r, g, b)

        # Now switch to new zone, skipping excluded zones
        for _ in range(len(self.zone_names)):  # Max iterations to avoid infinite loop
            self.current_zone_index = (self.current_zone_index + delta) % len(self.zone_names)
            zone_name = self._get_current_zone()

            # Skip excluded zones
            if self.should_skip_zone(zone_name):
                continue  # Try next zone
            else:
                break  # Found valid zone

        # Pulsing thread will automatically pick up the new zone (no restart needed)

        # Sync preview
        self._sync_preview()

        # Log zone change
        brightness = self.zone_brightness[zone_name]
        log.log(LogCategory.ZONE, "Zone changed", zone=zone_name, color=str(self.zone_colors[zone_name]), brightness=f"{brightness}%")

    def toggle_edit_mode(self):
        """Toggle edit mode ON/OFF"""
        self.edit_mode = not self.edit_mode

        if self.edit_mode:
            if self.main_mode == MainMode.STATIC:
                log.log(LogCategory.SYSTEM, "Edit mode enabled", mode=self.main_mode.name, parameter=self.current_param.name, zone=self._get_current_zone())
                self._start_pulse()
            else:
                log.log(LogCategory.SYSTEM, "Edit mode enabled", mode=self.main_mode.name, parameter=self.current_param.name, animation=self.animation_id)
            self._sync_preview()
        else:
            log.log(LogCategory.SYSTEM, "Edit mode disabled")
            self._stop_pulse()

    def quick_lamp_white(self):
        """
        Quick action: Toggle lamp white mode (BTN2)

        DESK LAMP MODE:
        - Lamp becomes independent desk lamp (warm white @ 100%)
        - Excluded from: zone selector, animations, pulsing, editing
        - Other zones work normally
        - Toggle again to restore previous state
        """
        if not self.lamp_white_mode:
            # ENTERING desk lamp mode
            self.lamp_white_saved_state = {
                "color": self.zone_colors["lamp"].to_dict(),
                "brightness": self.zone_brightness["lamp"]
            }
            self.lamp_white_mode = True

            # If lamp is currently selected, switch to next zone
            if self._get_current_zone() == "lamp":
                self.change_zone(1)
                log.log(LogCategory.SYSTEM, "Auto-switched zone", reason="lamp_white_mode enabled")

            # Set to warm white
            self.zone_colors["lamp"] = Color.from_preset("warm_white", self.color_manager)
            self.zone_brightness["lamp"] = 100

            # Apply to hardware (Color model preserves exact RGB: 255, 200, 150)
            r, g, b = self.zone_colors["lamp"].to_rgb()
            self.strip.set_zone_color("lamp", r, g, b)

            # Restart animation to exclude lamp
            if self.animation_engine.is_running():
                asyncio.create_task(self._restart_animation())

            log.log(LogCategory.SYSTEM, "Lamp white mode enabled", mode="Desk Lamp", excluded_from="zone selector, animations, pulsing")
        else:
            # EXITING desk lamp mode
            if self.lamp_white_saved_state:
                self.zone_colors["lamp"] = Color.from_dict(
                    self.lamp_white_saved_state["color"],
                    self.color_manager
                )
                self.zone_brightness["lamp"] = self.lamp_white_saved_state["brightness"]

                # Apply saved color
                r, g, b = self._get_zone_color("lamp")
                self.strip.set_zone_color("lamp", r, g, b)

                log.log(LogCategory.SYSTEM, "Lamp white mode disabled", lamp_color=str(self.zone_colors['lamp']), brightness=f"{self.zone_brightness['lamp']}%")

                self.lamp_white_saved_state = None

            self.lamp_white_mode = False

            # Restart animation to include lamp
            if self.animation_engine.is_running():
                asyncio.create_task(self._restart_animation())

    async def _restart_animation(self):
        """Restart animation with current exclusions (lamp_white_mode)"""
        await self.stop_animation()
        await self.start_animation()

    def power_toggle(self):
        """Toggle power for all zones (ON/OFF) - saves and restores brightness and animation state"""
        # Check if any zone has brightness > 0
        any_on = any(self.zone_brightness[zone] > 0 for zone in self.zone_names)

        if any_on:
            # Turning OFF: Save current brightness and animation state, then turn off
            if not hasattr(self, 'power_saved_brightness'):
                self.power_saved_brightness = {}

            # Save brightness
            for zone in self.zone_names:
                self.power_saved_brightness[zone] = self.zone_brightness[zone]

            # Save animation state and stop it
            self.power_saved_animation_enabled = self.animation_engine.is_running()
            if self.animation_engine.is_running():
                asyncio.create_task(self.stop_animation())

            # Turn off all zones
            for zone in self.zone_names:
                self.zone_brightness[zone] = 0
                self.strip.set_zone_color(zone, 0, 0, 0)

            self.preview_panel.clear()
            log.log(LogCategory.SYSTEM, "Power OFF", saved="brightness and animation state")
        else:
            # Turning ON: Restore saved brightness and animation state
            if hasattr(self, 'power_saved_brightness') and self.power_saved_brightness:
                # Restore saved brightness
                for zone in self.zone_names:
                    saved = self.power_saved_brightness.get(zone, 64)
                    self.zone_brightness[zone] = saved

                    # Apply color
                    r, g, b = self._get_zone_color(zone)
                    self.strip.set_zone_color(zone, r, g, b)
                log.log(LogCategory.SYSTEM, "Power ON", restored="saved brightness")
            else:
                # No saved state, use default brightness (50%)
                for zone in self.zone_names:
                    self.zone_brightness[zone] = 50

                    # Apply color
                    r, g, b = self._get_zone_color(zone)
                    self.strip.set_zone_color(zone, r, g, b)
                log.log(LogCategory.SYSTEM, "Power ON", brightness="default 50%")

            # Restore animation if it was running
            if hasattr(self, 'power_saved_animation_enabled') and self.power_saved_animation_enabled:
                asyncio.create_task(self.start_animation())
                log.log(LogCategory.ANIMATION, "Animation restarted after power ON")

            self._sync_preview()

    def clear_all(self):
        """Turn off all LEDs"""
        self.strip.clear()
        self.preview_panel.clear()
        log.log(LogCategory.SYSTEM, "All LEDs cleared")

    def _build_animation_params(self) -> Dict:
        """
        Build animation-specific parameters with zone brightness applied

        Animations receive colors that already have zone brightness baked in,
        so they match the brightness of static mode.

        Returns:
            Dict of animation parameters
        """
        params = {"speed": self.animation_speed}

        # Get current zone for reference (use its brightness/color)
        zone_tag = self._get_current_zone()

        if self.animation_id == "breathe":
            # Breathe: don't pass color parameter so animation uses per-zone cached colors
            # Colors will be cached in start_animation() via _cache_zone_colors()
            params["intensity"] = self.animation_intensity

        elif self.animation_id == "color_fade":
            if self.animation_color:
                params["start_hue"] = 0
            else:
                params["start_hue"] = self.zone_colors[zone_tag].to_hue()

        elif self.animation_id == "snake":
            if self.animation_color:
                # Apply current zone brightness to animation color
                brightness_scale = self.zone_brightness[zone_tag] / 100.0
                r, g, b = self.animation_color
                params["color"] = (int(r * brightness_scale), int(g * brightness_scale), int(b * brightness_scale))
            else:
                # Use zone color with brightness already applied
                params["color"] = self._get_zone_color(zone_tag)

        return params

    def _cache_zone_colors(self):
        """Cache current zone colors with brightness for breathe animation"""
        if not self.animation_engine.current_animation:
            return

        for zone_tag in self.zone_names:
            # Get color with brightness already applied
            r, g, b = self._get_zone_color(zone_tag)
            self.animation_engine.current_animation.set_zone_color_cache(zone_tag, r, g, b)

    async def start_animation(self):
        """Start the currently selected animation"""
        if self.animation_engine.is_running():
            log.log(LogCategory.ANIMATION, "Animation already running", level=LogLevel.INFO)
            return

        # Stop pulsing if active
        if self.edit_mode and self.pulse_active:
            self._stop_pulse()

        # Build parameters (with brightness already applied) and start animation
        params = self._build_animation_params()
        excluded_zones = self.get_excluded_zones()
        await self.animation_engine.start(self.animation_id, excluded_zones=excluded_zones, **params)

        # Cache zone colors for breathe animation (per-zone colors)
        if self.animation_id == "breathe":
            self._cache_zone_colors()

        log.log(LogCategory.ANIMATION, "Animation started", id=self.animation_id, speed=f"{self.animation_speed}/100")

    async def stop_animation(self):
        """Stop current animation and restore static colors"""
        if not self.animation_engine.is_running():
            return

        await self.animation_engine.stop()

        # Restore all zones to their static colors
        for zone_name in self.zone_names:
            r, g, b = self._get_zone_color(zone_name)
            self.strip.set_zone_color(zone_name, r, g, b)

        # Restart pulsing if edit mode is on
        if self.edit_mode:
            self._start_pulse()

        log.log(LogCategory.ANIMATION, "Animation stopped")

    async def _restart_animation(self):
        """Restart animation (stop then start with new animation_id)"""
        await self.stop_animation()
        await self.start_animation()

    def select_animation(self, delta):
        """
        Select animation (cycle through available animations)

        Automatically restarts animation if one is currently running.

        Args:
            delta: -1 for previous, +1 for next
        """
        was_running = self.animation_engine.is_running()

        self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animations)
        self.animation_id = self.available_animations[self.selected_animation_index]

        log.log(
            LogCategory.ANIMATION,
            "Animation selected",
            id=self.animation_id,
            index=f"{self.selected_animation_index + 1}/{len(self.available_animations)}"
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
        log_kwargs = {"animation_id": self.animation_id, "parameter": self.current_param.name}
        if self.current_param == ParamID.ANIM_SPEED:
            log_kwargs["speed"] = f"{self.animation_speed}/100"
        elif self.current_param == ParamID.ANIM_INTENSITY:
            log_kwargs["intensity"] = f"{self.animation_intensity}/100"
        log.log(LogCategory.SYSTEM, "Mode switched to ANIMATION", **log_kwargs)

    def _switch_to_static_mode(self):
        """Switch from ANIMATION to STATIC mode"""
        self.main_mode = MainMode.STATIC

        # Switch current param to first static param
        self.current_param = self.static_params[0]

        # Stop animation if running
        if self.animation_engine.is_running():
            asyncio.create_task(self.stop_animation())

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
        zone_name = self._get_current_zone()
        log_kwargs = {"zone": zone_name, "parameter": self.current_param.name}
        if self.current_param == ParamID.ZONE_COLOR_HUE:
            log_kwargs["hue"] = f"{self.zone_colors[zone_name].to_hue()}°"
        elif self.current_param == ParamID.ZONE_COLOR_PRESET:
            log_kwargs["preset"] = str(self.zone_colors[zone_name])
        elif self.current_param == ParamID.ZONE_BRIGHTNESS:
            log_kwargs["brightness"] = f"{self.zone_brightness[zone_name]}%"
        log.log(LogCategory.SYSTEM, "Mode switched to STATIC", **log_kwargs)

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
            asyncio.create_task(self.stop_animation())
        else:
            asyncio.create_task(self.start_animation())

    def _adjust_zone_parameter(self, zone_name: str, delta: int):
        """
        Adjust zone-specific parameter (hue, preset, brightness)

        Args:
            zone_name: Zone to adjust
            delta: Rotation direction (-1 or +1)
        """
        if self.current_param == ParamID.ZONE_COLOR_HUE:
            self.zone_colors[zone_name] = self.zone_colors[zone_name].adjust_hue(delta * 10)
            hue = self.zone_colors[zone_name].to_hue()
            r, g, b = self.zone_colors[zone_name].to_rgb()
            log.log(LogCategory.ZONE, "Hue adjusted", zone=zone_name, hue=f"{hue}°", rgb=f"({r},{g},{b})")
            self._sync_preview()

        elif self.current_param == ParamID.ZONE_COLOR_PRESET:
            self.zone_colors[zone_name] = self.zone_colors[zone_name].next_preset(delta, self.color_manager)
            log.log(LogCategory.ZONE, "Preset changed", zone=zone_name, preset=str(self.zone_colors[zone_name]))
            self._sync_preview()

        elif self.current_param == ParamID.ZONE_BRIGHTNESS:
            current = self.zone_brightness[zone_name]
            new_brightness = max(0, min(100, current + delta * 10))
            self.zone_brightness[zone_name] = new_brightness
            log.log(LogCategory.ZONE, "Brightness adjusted", zone=zone_name, brightness=f"{new_brightness}%")
            self._sync_preview()

    def _adjust_animation_parameter(self, delta: int):
        """
        Adjust animation-specific parameter (speed, intensity)

        Args:
            delta: Rotation direction (-1 or +1)
        """
        if self.current_param == ParamID.ANIM_SPEED:
            self.animation_speed = max(1, min(100, self.animation_speed + delta * 2))

            if self.animation_engine.is_running():
                self.animation_engine.update_param("speed", self.animation_speed)

            log.log(LogCategory.ANIMATION, "Speed adjusted", speed=f"{self.animation_speed}/100")
            self._sync_preview()

        elif self.current_param == ParamID.ANIM_INTENSITY:
            self.animation_intensity = max(1, min(100, self.animation_intensity + delta * 2))

            if self.animation_engine.is_running():
                self.animation_engine.update_param("intensity", self.animation_intensity)

            log.log(LogCategory.ANIMATION, "Intensity adjusted", intensity=f"{self.animation_intensity}/100")
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
            zone_name = self._get_current_zone()

            # Block editing excluded zones
            if self.should_skip_zone(zone_name):
                log.log(LogCategory.SYSTEM, "Zone is excluded from editing", zone=zone_name, reason="lamp_white_mode")
                return

            self._adjust_zone_parameter(zone_name, delta)
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
        else:  # ANIMATION mode
            params = self.animation_params

        # Cycle to next parameter
        idx = params.index(self.current_param)
        self.current_param = params[(idx + 1) % len(params)]

        # Update preview mode based on new parameter
        parameter = self.current_param
        if parameter == ParamID.ZONE_BRIGHTNESS:
            self.preview_mode = PreviewMode.BAR_INDICATOR
        elif parameter in (ParamID.ZONE_COLOR_HUE, ParamID.ZONE_COLOR_PRESET):
            self.preview_mode = PreviewMode.COLOR_DISPLAY
        elif parameter in [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]:
            self.preview_mode = PreviewMode.ANIMATION_PREVIEW

        self._sync_preview()

        # Log parameter switch
        zone_name = self._get_current_zone()

        if self.current_param == ParamID.ZONE_COLOR_HUE:
            hue = self.zone_colors[zone_name].to_hue()
            log.log(LogCategory.SYSTEM, "Parameter cycled", parameter=self.current_param.name, zone=zone_name, hue=f"{hue}°")
        elif self.current_param == ParamID.ZONE_COLOR_PRESET:
            log.log(LogCategory.SYSTEM, "Parameter cycled", parameter=self.current_param.name, zone=zone_name, preset=str(self.zone_colors[zone_name]))
        elif self.current_param == ParamID.ZONE_BRIGHTNESS:
            log.log(LogCategory.SYSTEM, "Parameter cycled", parameter=self.current_param.name, zone=zone_name, brightness=f"{self.zone_brightness[zone_name]}%")
        elif self.current_param == ParamID.ANIM_SPEED:
            log.log(LogCategory.SYSTEM, "Parameter cycled", parameter=self.current_param.name, speed=f"{self.animation_speed}/100")
        elif self.current_param == ParamID.ANIM_INTENSITY:
            log.log(LogCategory.SYSTEM, "Parameter cycled", parameter=self.current_param.name, intensity=f"{self.animation_intensity}/100")

    def get_status(self):
        """
        Get current status

        Returns:
            Dict with current state matching state.json structure (NEW FORMAT)
        """
        return {
            "main_mode": self.main_mode.name,  # STATIC or ANIMATION
            "current_param": self.current_param.name,  # Current parameter being edited
            "current_zone_index": self.current_zone_index,  # Remember selected zone
            "edit_mode": self.edit_mode,
            "lamp_white_mode": self.lamp_white_mode,
            "lamp_white_saved_state": self.lamp_white_saved_state,
            "animation": {
                "enabled": self.animation_engine.is_running(),
                "id": self.animation_id,
                "speed": self.animation_speed,
                "color": self.animation_color,
                "color2": self.animation_color2,
                "intensity": self.animation_intensity
            },
            "zones": {
                zone: {
                    "color": self.zone_colors[zone].to_dict(),
                    "brightness": self.zone_brightness[zone]  # 0-100%
                }
                for zone in self.zone_names
            }
        }

