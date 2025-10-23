"""
LED Controller - Business logic with state machine

Manages LED strips and preview panel with multiple modes:
- COLOR_EDIT: Adjust color (hue)
- BRIGHTNESS_EDIT: Adjust brightness
- (Future: ANIMATION_SELECT, SPEED_EDIT, etc.)

Hardware:
- Preview Panel: GPIO 19, 8 LEDs, GRB (CJMCU-2812-8)
- LED Strip: GPIO 18, 33 pixels, BRG (WS2811)
  Zones: lamp(19px), top(4px), right(3px), bottom(4px), left(3px)
"""

from rpi_ws281x import ws, Color as RGBColor  # Rename to avoid conflict with models.Color
from components import PreviewPanel, ZoneStrip
from utils import hue_to_rgb
from utils.logger import get_logger
from animations import AnimationEngine
from models import Color, ColorMode, MainMode, PreviewMode, ParamID
from models import load_parameters, get_parameter
from managers.color_manager import ColorManager
from managers.animation_manager import AnimationManager
import time
import math
import asyncio


# Parameter cycling order for each mode
STATIC_PARAMS = [ParamID.ZONE_COLOR_HUE, ParamID.ZONE_COLOR_PRESET, ParamID.ZONE_BRIGHTNESS]
ANIMATION_PARAMS = [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]


class LEDController:
    """
    LED Controller with state machine

    Manages:
        - Preview panel (8 LEDs, GPIO 19, GRB)
        - Main strip (33 pixels, GPIO 18, BRG)
        - 5 zones: lamp, top, right, bottom, left

    Modes:
        - COLOR_EDIT: Modulator changes hue
        - BRIGHTNESS_EDIT: Modulator changes brightness

    Example:
        led = LEDController()

        # Change zone
        led.change_zone(1)  # Next zone

        # Adjust color
        led.adjust_hue(10)  # +10 degrees

        # Change mode
        led.switch_mode()  # COLOR_EDIT -> BRIGHTNESS_EDIT
    """

    def __init__(self, config_manager, state):
        """
        Initialize LED Controller

        Args:
            config_manager: ConfigManager instance (provides all config + sub-managers)
            state: State dict loaded from state.json

        Architecture:
            ConfigManager is the single source of truth for all configuration.
            LEDController receives managers via dependency injection.
        """
        self.config_manager = config_manager
        self.state = state

        # Initialize logger
        self.logger = get_logger()

        # Get managers from ConfigManager (dependency injection)
        self.color_manager: ColorManager = config_manager.color_manager
        self.animation_manager: AnimationManager = config_manager.animation_manager

        # Load parameters (global registry)
        load_parameters()  # Populates global PARAMETERS registry

        # Get zones from ConfigManager
        zones = config_manager.zones  # Dict[str, [start, end]]
        self.zone_names = list(zones.keys())

        # Hardware setup via HardwareManager (dependency injection)
        # Preview and Strip are on SEPARATE GPIOs
        # Preview: GPIO 19, RGB hardware
        # Strip: GPIO 18, BRG hardware
        hardware_manager = config_manager.hardware_manager

        preview_config = hardware_manager.get_led_strip("preview")
        self.preview = PreviewPanel(
            gpio=preview_config["gpio"],  # Separate GPIO for preview
            count=preview_config["count"],
            color_order=ws.WS2811_STRIP_GRB,  # Preview panel is GRB (CJMCU-2812-8)
            brightness=preview_config["brightness"]  # Full hardware brightness
        )

        strip_config = hardware_manager.get_led_strip("strip")
        self.strip = ZoneStrip(
            gpio=strip_config["gpio"],  # Separate GPIO for strip
            pixel_count=strip_config["count"],  # Total: 99 physical LEDs / 3 = 33 pixels
            zones=zones,
            color_order=ws.WS2811_STRIP_BRG,  # Strip uses BRG
            brightness=strip_config["brightness"]  # Full hardware brightness
        )

        # Global state
        self.edit_mode = state.get("edit_mode", True)

        # Lamp white mode (desk lamp mode - lamp excluded from everything)
        self.lamp_white_mode = state.get("lamp_white_mode", False)
        self.lamp_white_saved_state = state.get("lamp_white_saved_state", None)

        # Two-mode system (STATIC vs ANIMATION) - load from state
        try:
            self.main_mode = MainMode[state.get("main_mode", "STATIC")]
        except KeyError:
            self.main_mode = MainMode.STATIC

        # Current parameter (using ParamID)
        try:
            self.current_param = ParamID[state.get("current_param", "ZONE_COLOR_HUE")]
        except KeyError:
            self.current_param = ParamID.ZONE_COLOR_HUE

        # Set preview_mode based on current mode and parameter
        if self.main_mode == MainMode.STATIC:
            if self.current_param == ParamID.ZONE_BRIGHTNESS:
                self.preview_mode = PreviewMode.BAR_INDICATOR
            else:
                self.preview_mode = PreviewMode.COLOR_DISPLAY
        else:  # ANIMATION mode
            self.preview_mode = PreviewMode.BAR_INDICATOR

        # Zone selection - load from state
        self.zone_names = list(zones.keys())
        self.current_zone_index = state.get("current_zone_index", 0)

        # Parameters per zone (using Color model)
        self.zone_colors = {}  # Dict[str, Color] - SINGLE SOURCE OF TRUTH
        self.zone_brightness = {}  # Dict[str, int] - 0-100%

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
        self.animation_engine = AnimationEngine(self.strip, zones)

        # Animation state from config
        anim_state = state.get("animation", {})
        # Store whether animation should auto-start (for state persistence)
        self._animation_should_run = anim_state.get("enabled", False)
        self.animation_name = anim_state.get("name", "breathe")
        self.animation_speed = anim_state.get("speed", 50)
        self.animation_color = anim_state.get("color", None)  # None = use zone colors
        self.animation_color2 = anim_state.get("color2", None)
        self.animation_intensity = anim_state.get("intensity", 100)

        # FUTURE-PROOF: Per-zone animation state (for HYBRID mode)
        # This prepares architecture for per-zone animations without breaking current code
        # In HYBRID mode, each zone can have its own animation running independently
        self.zone_animations = {}
        for zone_name in self.zone_names:
            zone_anim_state = state.get("zones", {}).get(zone_name, {}).get("animation", {})
            self.zone_animations[zone_name] = {
                "enabled": zone_anim_state.get("enabled", False),
                "name": zone_anim_state.get("name", "breathe"),
                "speed": zone_anim_state.get("speed", 50),
                "intensity": zone_anim_state.get("intensity", 100),
            }

        # Animation list for selection (ordered)
        self.available_animations = ["breathe", "color_fade", "snake", "color_snake"]
        self.selected_animation_index = 0
        if self.animation_name in self.available_animations:
            self.selected_animation_index = self.available_animations.index(self.animation_name)

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

        # Sync preview with current zone
        self._sync_preview()

    def _sync_preview(self):
        """
        Sync preview panel based on current mode and preview_mode
        This is the central dispatcher for preview updates
        """
        if self.preview_mode == PreviewMode.COLOR_DISPLAY:
            self._preview_show_color()
        elif self.preview_mode == PreviewMode.BAR_INDICATOR:
            self._preview_show_bar()
        elif self.preview_mode == PreviewMode.ANIMATION_PREVIEW:
            self._preview_show_animation()

    def _preview_show_color(self):
        """Preview: Show color on all 8 LEDs"""
        zone_name = self._get_current_zone()

        # Get RGB from Color model (handles HUE/PRESET/WHITE automatically)
        r, g, b = self.zone_colors[zone_name].to_rgb()

        # Apply brightness
        brightness = self.zone_brightness[zone_name]
        scale = brightness / 100.0  # Changed from /255 to /100
        r, g, b = int(r * scale), int(g * scale), int(b * scale)

        self.preview.set_color(r, g, b)

    def _preview_show_bar(self):
        """
        Preview: Show LED bar (N of 8 LEDs) for numeric value

        NEW: For BRIGHTNESS parameter - 8 discrete levels
        - Level is determined by brightness value (0-255 divided into 8 levels)
        - Number of LEDs = level (1-8)
        - LED brightness = zone brightness (same as actual zone)
        - Example: brightness=128 → level 4 → 4 LEDs at brightness 128
        """
        zone_name = self._get_current_zone()

        # Determine what value to show based on current parameter
        # NEW: Use main_mode + static_parameter / animation_parameter
        value = None
        max_value = 100
        base_color = (255, 255, 255)
        is_brightness_param = False

        if self.main_mode == MainMode.STATIC:
            if self.current_param == ParamID.ZONE_BRIGHTNESS:
                value = self.zone_brightness[zone_name]
                max_value = 100  # Changed from 255 to 100%
                # Get zone color at FULL brightness
                base_color = self.zone_colors[zone_name].to_rgb()
                is_brightness_param = True
        elif self.main_mode == MainMode.ANIMATION:
            if self.current_param == ParamID.ANIM_SPEED:
                value = self.animation_speed
                max_value = 100
                base_color = (128, 128, 128)  # Gray bar for speed
            elif self.current_param == ParamID.ANIM_INTENSITY:
                value = self.animation_intensity
                max_value = 100
                base_color = (128, 128, 128)  # Gray bar for intensity

        # Fallback to color display if no bar-compatible parameter
        if value is None:
            self._preview_show_color()
            return

        # Calculate level (0-8) and actual LED brightness
        if is_brightness_param:
            # For brightness: 8 discrete levels based on brightness value
            # Level 0: 0 LEDs, Level 1: 1 LED at brightness X, ..., Level 8: 8 LEDs at brightness X
            if value == 0:
                num_leds = 0
                led_brightness = 0
            else:
                # Map 1-255 to levels 1-8
                num_leds = max(1, min(8, int((value / max_value) * 8) + (1 if value % 32 > 0 else 0)))
                # LED brightness = zone brightness (no scaling)
                led_brightness = value / 255.0
        else:
            # For other parameters: traditional bar (0-8 LEDs at full brightness)
            num_leds = max(0, min(8, int((value / max_value) * 8)))
            led_brightness = 1.0

        # Apply brightness to color
        r, g, b = base_color
        r = int(r * led_brightness)
        g = int(g * led_brightness)
        b = int(b * led_brightness)

        # Set LED bar (right to left, since CJMCU is upside down)
        for i in range(8):
            # Reverse index: 0->7, 1->6, 2->5, etc.
            reversed_i = 7 - i
            if i < num_leds:
                self.preview.strip.setPixelColor(reversed_i, RGBColor(r, g, b))
            else:
                self.preview.strip.setPixelColor(reversed_i, RGBColor(0, 0, 0))
        self.preview.strip.show()

    def _preview_show_animation(self):
        """Preview: Show mini animation (placeholder for now)"""
        # TODO: Implement mini animations for preview
        # For now, just show the selected animation name color
        if self.animation_color:
            r, g, b = self.animation_color
        else:
            # Show current zone color as preview
            zone_name = self._get_current_zone()
            r, g, b = self._get_zone_color(zone_name)
        self.preview.set_color(r, g, b)

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
        """Get current zone name"""
        return self.zone_names[self.current_zone_index]

    async def _pulse_zone_thread(self):
        """Background thread that pulses the currently selected zone"""
        cycle_duration = 1.0  # 1 second per pulse cycle (faster)
        steps = 40  # Number of steps in one cycle

        while self.pulse_active:
            for step in range(steps):
                if not self.pulse_active:
                    break

                # Get CURRENT zone and color (dynamically, not cached)
                zone_name = self._get_current_zone()

                # Use Color model as single source of truth
                r, g, b = self.zone_colors[zone_name].to_rgb()

                base_brightness = self.zone_brightness[zone_name]

                # Sine wave for smooth pulsing (0.1 to 1.0 multiplier - deeper fade)
                t = step / steps
                brightness_scale = 0.1 + 0.9 * (math.sin(t * 2 * math.pi - math.pi/2) + 1) / 2

                # Apply pulsing brightness
                pulsed_brightness = base_brightness * brightness_scale
                scale = pulsed_brightness / 255.0
                r, g, b = int(r * scale), int(g * scale), int(b * scale)

                # with self.pulse_lock:
                async with self.pulse_lock:
                    self.strip.set_zone_color(zone_name, r, g, b)

                # time.sleep(cycle_duration / steps)
                await asyncio.sleep(cycle_duration / steps)
                
    async def _pulse_zone_task(self):
        """Async pulsing animation for current zone - fixed 1s cycle"""
        cycle_duration = 1.0  # Fixed 1 second pulse cycle (independent from animation_speed)
        steps = 40

        while self.pulse_active:
            for step in range(steps):
                if not self.pulse_active:
                    break

                zone_name = self._get_current_zone()

                # SKIP pulsing lamp if lamp_white_mode is ON (lamp is in white mode)
                if zone_name == "lamp" and self.lamp_white_mode:
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

        # Now switch to new zone, SKIPPING lamp if lamp_white_mode is active
        for _ in range(len(self.zone_names)):  # Max iterations to avoid infinite loop
            self.current_zone_index = (self.current_zone_index + delta) % len(self.zone_names)
            zone_name = self._get_current_zone()

            # Skip lamp if lamp_white_mode is ON
            if zone_name == "lamp" and self.lamp_white_mode:
                continue  # Try next zone
            else:
                break  # Found valid zone

        # Pulsing thread will automatically pick up the new zone (no restart needed)

        # Sync preview
        self._sync_preview()

        # Print feedback
        brightness = self.zone_brightness[zone_name]
        print(f"\n>>> Zone: {zone_name}")
        print(f"    Color: {self.zone_colors[zone_name]}, Brightness: {brightness}%")

    def toggle_edit_mode(self):
        """Toggle edit mode ON/OFF"""
        self.edit_mode = not self.edit_mode

        if self.edit_mode:
            print(f"\n>>> EDIT MODE: ON")
            print(f"    Main Mode: {self.main_mode.name}")
            print(f"    Current Parameter: {self.current_param.name}")
            if self.main_mode == MainMode.STATIC:
                print(f"    Zone: {self._get_current_zone()}")
                self._start_pulse()  # Start pulsing the selected zone
            else:
                print(f"    Animation: {self.animation_name}")
            self._sync_preview()
        else:
            print(f"\n>>> EDIT MODE: OFF")
            self._stop_pulse()  # Stop pulsing and restore color

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
                print("    (Auto-switched to next zone)")

            # Set to warm white
            self.zone_colors["lamp"] = Color.from_preset("warm_white", self.color_manager)
            self.zone_brightness["lamp"] = 100

            # Apply to hardware (Color model preserves exact RGB: 255, 200, 150)
            r, g, b = self.zone_colors["lamp"].to_rgb()
            self.strip.set_zone_color("lamp", r, g, b)

            # Restart animation to exclude lamp
            if self.animation_engine.is_running():
                asyncio.create_task(self._restart_animation())

            print("\n>>> LAMP WHITE MODE: ON")
            print("    Lamp -> Desk Lamp (warm white @ 100%)")
            print("    Excluded from: zone selector, animations, pulsing")
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

                print("\n>>> LAMP WHITE MODE: OFF")
                print(f"    Lamp restored: {self.zone_colors['lamp']}, brightness={self.zone_brightness['lamp']}%")

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

            self.preview.clear()
            print("\n>>> POWER: OFF (brightness and animation saved)")
        else:
            # Turning ON: Restore saved brightness and animation state
            if hasattr(self, 'power_saved_brightness') and self.power_saved_brightness:
                # Restore saved brightness
                for zone in self.zone_names:
                    saved = self.power_saved_brightness.get(zone, 64)
                    self.zone_brightness[zone] = saved

                    # Apply color (lamp_white_mode handled by zone_colors already)
                    r, g, b = self._get_zone_color(zone)
                    self.strip.set_zone_color(zone, r, g, b)
                print("\n>>> POWER: ON (brightness restored)")
            else:
                # No saved state, use default brightness (50%)
                for zone in self.zone_names:
                    self.zone_brightness[zone] = 50

                    # Apply color (lamp_white_mode handled by zone_colors already)
                    r, g, b = self._get_zone_color(zone)
                    self.strip.set_zone_color(zone, r, g, b)
                print("\n>>> POWER: ON (default brightness)")

            # Restore animation if it was running
            if hasattr(self, 'power_saved_animation_enabled') and self.power_saved_animation_enabled:
                asyncio.create_task(self.start_animation())
                print("    Animation restarted")

            self._sync_preview()

    def clear_all(self):
        """Turn off all LEDs"""
        self.strip.clear()
        self.preview.clear()
        print(">>> All LEDs cleared")

    async def start_animation(self):
        """Start the currently selected animation"""
        # Check if animation is actually running (not just the flag)
        if self.animation_engine.is_running():
            print("[INFO] Animation already running")
            return

        # Stop pulsing if active
        if self.edit_mode and self.pulse_active:
            self._stop_pulse()

        # Prepare animation parameters
        params = {
            "speed": self.animation_speed,
        }

        # Add animation-specific parameters
        if self.animation_name == "breathe":
            params["color"] = self.animation_color
            params["intensity"] = self.animation_intensity
        elif self.animation_name == "color_fade":
            # Use current zone hue as starting point if no color specified
            if self.animation_color:
                # Convert RGB to hue (approximate)
                params["start_hue"] = 0
            else:
                zone_name = self._get_current_zone()
                params["start_hue"] = self.zone_colors[zone_name].to_hue()
        elif self.animation_name == "snake":
            if self.animation_color:
                params["color"] = tuple(self.animation_color)
            else:
                params["color"] = (255, 255, 255)

        # Exclude lamp from animation if lamp_white_mode is ON
        excluded_zones = ["lamp"] if self.lamp_white_mode else []

        # Start animation via engine
        await self.animation_engine.start(self.animation_name, excluded_zones=excluded_zones, **params)

        # Cache brightness values for animations
        for zone_name in self.zone_names:
            brightness = self.zone_brightness[zone_name]
            self.animation_engine.current_animation.set_zone_brightness_cache(zone_name, brightness)

        print(f"\n>>> ANIMATION STARTED: {self.animation_name}")
        print(f"    Speed: {self.animation_speed}/100")

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

        print(f"\n>>> ANIMATION STOPPED")

    def select_animation(self, delta):
        """
        Select animation in ANIMATION_SELECT mode

        Args:
            delta: -1 for previous, +1 for next
        """
        if self.mode != Mode.ANIMATION_SELECT:
            return

        self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animations)
        self.animation_name = self.available_animations[self.selected_animation_index]

        print(f"\n>>> Animation: {self.animation_name}")
        print(f"    [{self.selected_animation_index + 1}/{len(self.available_animations)}]")

        # Update preview
        self._sync_preview()

    # ===== NEW: Unified Parameter System =====

    def cycle_parameter(self):
        """
        Cycle through parameters (Upper encoder CLICK)
        COLOR → BRIGHTNESS → ANIMATION → ANIM_SPEED → ANIM_INTENSITY → (loop)

        Only works when edit_mode=ON
        """
        if not self.edit_mode:
            print("[INFO] Enter edit mode first to cycle parameters")
            return

        # Cycle through parameters
        params = list(Parameter)
        idx = params.index(self.current_parameter)
        self.current_parameter = params[(idx + 1) % len(params)]

        # Update preview_mode based on new parameter
        if self.current_parameter == Parameter.COLOR:
            self.preview_mode = PreviewMode.COLOR_DISPLAY
        elif self.current_parameter == Parameter.BRIGHTNESS:
            self.preview_mode = PreviewMode.BAR_INDICATOR
        elif self.current_parameter == Parameter.ANIMATION:
            self.preview_mode = PreviewMode.ANIMATION_PREVIEW
        elif self.current_parameter in (Parameter.ANIM_SPEED, Parameter.ANIM_INTENSITY):
            self.preview_mode = PreviewMode.BAR_INDICATOR

        self._sync_preview()
        print(f"\n>>> Parameter: {self.current_parameter.name}")

        # Show current value
        if self.current_parameter == Parameter.COLOR:
            zone_name = self._get_current_zone()
            hue = self.zone_hues[zone_name]
            print(f"    Color Mode: {self.color_mode.name}, Hue: {hue}°")
        elif self.current_parameter == Parameter.BRIGHTNESS:
            zone_name = self._get_current_zone()
            brightness = self.zone_brightness[zone_name]
            print(f"    Brightness: {brightness}/255")
        elif self.current_parameter == Parameter.ANIMATION:
            print(f"    Animation: {self.animation_name} [{self.selected_animation_index + 1}/{len(self.available_animations)}]")
        elif self.current_parameter == Parameter.ANIM_SPEED:
            print(f"    Speed: {self.animation_speed}/100")
        elif self.current_parameter == Parameter.ANIM_INTENSITY:
            print(f"    Intensity: {self.animation_intensity}/100")

    def adjust_parameter(self, delta):
        """
        Adjust currently selected parameter value (Lower encoder ROTATION)
        Dispatches to appropriate handler based on current_parameter

        Only works when edit_mode=ON
        """
        if not self.edit_mode:
            return

        zone_name = self._get_current_zone()

        # Block editing lamp when in white mode
        if zone_name == "lamp" and self.lamp_white_mode and self.current_parameter in (Parameter.COLOR, Parameter.BRIGHTNESS):
            print("[INFO] Lamp is in white mode - press BTN2 to exit and enable editing")
            return

        if self.current_parameter == Parameter.COLOR:
            # Adjust color (HUE or PRESET)
            if self.color_mode == ColorMode.HUE:
                self.zone_hues[zone_name] = (self.zone_hues[zone_name] + delta * 10) % 360
                hue = self.zone_hues[zone_name]
                r, g, b = hue_to_rgb(hue)
                print(f">>> {zone_name}: Hue = {hue}° (RGB: {r}, {g}, {b})")
            else:  # PRESET
                self.zone_preset_indices[zone_name] = (self.zone_preset_indices[zone_name] + delta) % len(PRESET_ORDER)
                preset_idx = self.zone_preset_indices[zone_name]
                preset_name, (r, g, b) = get_preset_by_index(preset_idx)

                # Convert preset RGB to HUE and save it
                from utils.colors import rgb_to_hue
                hue = rgb_to_hue(r, g, b)
                self.zone_hues[zone_name] = hue

                print(f">>> {zone_name}: Preset = '{preset_name}' (Hue: {hue}°)")

            self._sync_preview()

        elif self.current_parameter == Parameter.BRIGHTNESS:
            # Adjust brightness (8 levels: 0, 32, 64, 96, 128, 160, 192, 224, 255)
            current = self.zone_brightness[zone_name]
            current_level = round(current / 32)
            new_level = max(0, min(8, current_level + delta))
            new_brightness = new_level * 32
            if new_level == 8:
                new_brightness = 255

            self.zone_brightness[zone_name] = new_brightness
            self._sync_preview()
            print(f">>> {zone_name}: Brightness = {new_brightness}/255 (level {new_level}/8)")

        elif self.current_parameter == Parameter.ANIMATION:
            # Select animation
            self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animations)
            self.animation_name = self.available_animations[self.selected_animation_index]
            print(f"\n>>> Animation: {self.animation_name}")
            print(f"    [{self.selected_animation_index + 1}/{len(self.available_animations)}]")
            self._sync_preview()

        elif self.current_parameter == Parameter.ANIM_SPEED:
            # Adjust animation speed
            self.animation_speed = max(1, min(100, self.animation_speed + delta * 2))

            # Update live if animation is running
            if self.animation_engine.is_running():
                self.animation_engine.update_param("speed", self.animation_speed)

            print(f">>> Animation speed = {self.animation_speed}/100")
            self._sync_preview()

        elif self.current_parameter == Parameter.ANIM_INTENSITY:
            # Adjust animation intensity
            self.animation_intensity = max(1, min(100, self.animation_intensity + delta * 2))

            # Update live if animation is running
            if self.animation_engine.is_running():
                self.animation_engine.update_param("intensity", self.animation_intensity)

            print(f">>> Animation intensity = {self.animation_intensity}/100")
            self._sync_preview()

    def parameter_click(self):
        """
        Context-sensitive action for Lower encoder CLICK

        - COLOR parameter: Toggle HUE ↔ PRESET
        - ANIMATION parameter: Start/Stop animation
        - Other parameters: No action (or could cycle sub-parameters)
        """
        if self.current_parameter == Parameter.COLOR:
            # Toggle HUE <-> PRESET
            if self.color_mode == ColorMode.HUE:
                self.color_mode = ColorMode.PRESET
            else:
                self.color_mode = ColorMode.HUE

            print(f"\n>>> Color Mode: {self.color_mode.name}")
            self._sync_preview()

        elif self.current_parameter == Parameter.ANIMATION:
            # Toggle animation ON/OFF
            if self.animation_engine.is_running():
                asyncio.create_task(self.stop_animation())
            else:
                asyncio.create_task(self.start_animation())

        # Other parameters: no click action (can be extended later)

    # ===== NEW: Two-Mode System (STATIC vs ANIMATION) =====

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
            # Switch to ANIMATION mode
            self.main_mode = MainMode.ANIMATION

            # Stop pulsing (animation mode doesn't pulse zones)
            if self.pulse_active:
                self._stop_pulse()

            # Set preview to animation preview
            self.preview_mode = PreviewMode.ANIMATION_PREVIEW
            self._sync_preview()

            # Switch current param to first animation param
            self.current_param = ANIMATION_PARAMS[0]

            # Auto-start animation if not already running
            if not self.animation_engine.is_running():
                asyncio.create_task(self.start_animation())

            print(f"\n>>> MODE: ANIMATION")
            print(f"    Current animation: {self.animation_name}")
            print(f"    Parameter: {self.current_param.name}")
            if self.current_param == ParamID.ANIM_SPEED:
                print(f"    Speed: {self.animation_speed}/100")
            elif self.current_param == ParamID.ANIM_INTENSITY:
                print(f"    Intensity: {self.animation_intensity}/100")

        else:
            # Switch to STATIC mode
            self.main_mode = MainMode.STATIC

            # Switch current param to first static param
            self.current_param = STATIC_PARAMS[0]

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

            zone_name = self._get_current_zone()
            print(f"\n>>> MODE: STATIC")
            print(f"    Zone: {zone_name}")
            print(f"    Parameter: {self.current_param.name}")
            if self.current_param == ParamID.ZONE_COLOR_HUE:
                hue = self.zone_colors[zone_name].to_hue()
                print(f"    Hue: {hue}°")
            elif self.current_param == ParamID.ZONE_COLOR_PRESET:
                print(f"    Preset: {self.zone_colors[zone_name]}")
            elif self.current_param == ParamID.ZONE_BRIGHTNESS:
                print(f"    Brightness: {self.zone_brightness[zone_name]}%")

    def handle_upper_rotation(self, delta):
        """
        Handle upper encoder ROTATION (context-sensitive)

        STATIC mode: Change zone
        ANIMATION mode: Select animation
        """
        if self.main_mode == MainMode.STATIC:
            # Change zone
            self.change_zone(delta)

        else:  # ANIMATION mode
            # Select animation
            self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animations)
            self.animation_name = self.available_animations[self.selected_animation_index]

            print(f"\n>>> Animation: {self.animation_name}")
            print(f"    [{self.selected_animation_index + 1}/{len(self.available_animations)}]")
            self._sync_preview()

    def handle_upper_click(self):
        """
        Handle upper encoder CLICK (context-sensitive)

        STATIC mode: (unused)
        ANIMATION mode: Start/Stop animation
        """
        if not self.edit_mode:
            print("[INFO] Enter edit mode first (BTN1)")
            return

        if self.main_mode == MainMode.STATIC:
            # Unused in STATIC mode
            print("[INFO] Upper encoder click unused in STATIC mode")
            print("      Use lower encoder click to cycle parameters")
            return

        # ANIMATION mode: Toggle animation ON/OFF
        if self.animation_engine.is_running():
            asyncio.create_task(self.stop_animation())
        else:
            asyncio.create_task(self.start_animation())

    def handle_lower_rotation(self, delta):
        """
        Handle lower encoder ROTATION (context-sensitive)

        STATIC mode: Adjust parameter value (color, brightness)
        ANIMATION mode: Adjust parameter value (speed, intensity)
        """
        if not self.edit_mode:
            return

        if self.main_mode == MainMode.STATIC:
            zone_name = self._get_current_zone()

            # Block editing lamp when in white mode
            if zone_name == "lamp" and self.lamp_white_mode:
                print("[INFO] Lamp is in white mode - press BTN2 to exit")
                return

            if self.current_param == ParamID.ZONE_COLOR_HUE:
                # Adjust HUE using Color model
                # Pulsing thread will automatically pick up the new color
                self.zone_colors[zone_name] = self.zone_colors[zone_name].adjust_hue(delta * 10)
                hue = self.zone_colors[zone_name].to_hue()
                r, g, b = self.zone_colors[zone_name].to_rgb()
                print(f">>> {zone_name}: Hue = {hue}° (RGB: {r}, {g}, {b})")
                self._sync_preview()

            elif self.current_param == ParamID.ZONE_COLOR_PRESET:
                # Cycle through presets using Color model
                # Pulsing thread will automatically pick up the new color
                self.zone_colors[zone_name] = self.zone_colors[zone_name].next_preset(delta, self.color_manager)
                print(f">>> {zone_name}: Preset = {self.zone_colors[zone_name]}")
                self._sync_preview()

            elif self.current_param == ParamID.ZONE_BRIGHTNESS:
                # Adjust BRIGHTNESS (0-100%, 10 levels: 0, 10, 20, ..., 100)
                # Pulsing thread will automatically pick up the new brightness
                current = self.zone_brightness[zone_name]
                new_brightness = max(0, min(100, current + delta * 10))
                self.zone_brightness[zone_name] = new_brightness
                print(f">>> {zone_name}: Brightness = {new_brightness}%")
                self._sync_preview()

        else:  # ANIMATION mode
            if self.current_param == ParamID.ANIM_SPEED:
                # Adjust speed
                self.animation_speed = max(1, min(100, self.animation_speed + delta * 2))

                # Update live if animation running
                if self.animation_engine.is_running():
                    self.animation_engine.update_param("speed", self.animation_speed)

                print(f">>> Animation speed = {self.animation_speed}/100")
                self._sync_preview()

            elif self.current_param == ParamID.ANIM_INTENSITY:
                # Adjust intensity
                self.animation_intensity = max(1, min(100, self.animation_intensity + delta * 2))

                # Update live if animation running
                if self.animation_engine.is_running():
                    self.animation_engine.update_param("intensity", self.animation_intensity)

                print(f">>> Animation intensity = {self.animation_intensity}/100")
                self._sync_preview()

    def handle_lower_click(self):
        """
        Handle lower encoder CLICK (context-sensitive)

        Both modes: Cycle parameters
        """
        if not self.edit_mode:
            print("[INFO] Enter edit mode first (BTN1)")
            return

        # Get appropriate cycling list based on mode
        if self.main_mode == MainMode.STATIC:
            params = STATIC_PARAMS
        else:  # ANIMATION mode
            params = ANIMATION_PARAMS

        # Cycle to next parameter
        idx = params.index(self.current_param)
        self.current_param = params[(idx + 1) % len(params)]

        # Update preview mode based on new parameter
        if self.current_param == ParamID.ZONE_BRIGHTNESS:
            self.preview_mode = PreviewMode.BAR_INDICATOR
        elif self.current_param in [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]:
            self.preview_mode = PreviewMode.BAR_INDICATOR
        else:
            self.preview_mode = PreviewMode.COLOR_DISPLAY

        self._sync_preview()

        # Print parameter info
        zone_name = self._get_current_zone()
        print(f"\n>>> Parameter: {self.current_param.name}")

        if self.current_param == ParamID.ZONE_COLOR_HUE:
            hue = self.zone_colors[zone_name].to_hue()
            print(f"    Zone: {zone_name}, Hue: {hue}°")
        elif self.current_param == ParamID.ZONE_COLOR_PRESET:
            print(f"    Zone: {zone_name}, Preset: {self.zone_colors[zone_name]}")
        elif self.current_param == ParamID.ZONE_BRIGHTNESS:
            print(f"    Zone: {zone_name}, Brightness: {self.zone_brightness[zone_name]}%")
        elif self.current_param == ParamID.ANIM_SPEED:
            print(f"    Speed: {self.animation_speed}/100")
        elif self.current_param == ParamID.ANIM_INTENSITY:
            print(f"    Intensity: {self.animation_intensity}/100")

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
                "name": self.animation_name,
                "speed": self.animation_speed,
                "color": self.animation_color,
                "color2": self.animation_color2,
                "intensity": self.animation_intensity
            },
            "zones": {
                zone: {
                    "color": self.zone_colors[zone].to_dict(),  # NEW: Color.to_dict()
                    "brightness": self.zone_brightness[zone]  # 0-100%
                }
                for zone in self.zone_names
            }
        }

