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

from enum import Enum, auto
from rpi_ws281x import ws, Color
from components import PreviewPanel, ZoneStrip
from utils import hue_to_rgb, get_preset_by_index, PRESET_ORDER
from animations import AnimationEngine
import time
import math
import asyncio

class Mode(Enum):
    """Main operating modes for the LED controller"""
    COLOR_SELECT = auto()
    BRIGHTNESS_ADJUST = auto()
    ANIMATION_SELECT = auto()
    ANIMATION_PARAM = auto()


class ColorMode(Enum):
    """Sub-modes for color selection"""
    HUE = auto()      # Smooth hue rotation 0-360
    PRESET = auto()   # Jump between preset colors


class AnimationParamMode(Enum):
    """Sub-modes for animation parameters"""
    SPEED = auto()
    COLOR1 = auto()
    COLOR2 = auto()
    INTENSITY = auto()


class PreviewMode(Enum):
    """Preview panel display modes"""
    COLOR_DISPLAY = auto()    # Show color on all 8 LEDs
    BAR_INDICATOR = auto()    # LED bar (N of 8 LEDs lit)
    ANIMATION_PREVIEW = auto() # Mini animation running



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

    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        zones = self.config["zones"]
        self.zone_names = list(zones.keys())
        
        # Hardware setup
        # Preview and Strip are on SEPARATE GPIOs
        # Preview: GPIO 19, RGB hardware
        # Strip: GPIO 18, BRG hardware
        preview_config = self.config["hardware"]["leds"]["preview"]
        
        self.preview = PreviewPanel(
            gpio=preview_config["gpio"],  # Separate GPIO for preview
            count=preview_config["count"],
            color_order=ws.WS2811_STRIP_GRB,  # Preview panel is GRB (CJMCU-2812-8)
            #color_order=preview_config["color_order"],  # Preview panel is GRB (CJMCU-2812-8)
            brightness=preview_config["brightness"]  # Full hardware brightness
        )

        strip_config = self.config["hardware"]["leds"]["strip"]
        
        self.strip = ZoneStrip(
            gpio=strip_config["gpio"],  # Separate GPIO for strip
            pixel_count=strip_config["count"],  # Total: 99 physical LEDs / 3 = 33 pixels
            zones=zones,
            color_order=ws.WS2811_STRIP_BRG,  # Strip uses BRG
            brightness=strip_config["brightness"]  # Full hardware brightness
        )

        # Global state
        self.edit_mode = state.get("edit_mode", True)
        self.lamp_solo = state.get("lamp_solo", False)
        self.lamp_solo_state = state.get("lamp_solo_state", None)

        # Main mode state
        self.mode = Mode[state.get("mode", "COLOR_SELECT")]
        self.color_mode = ColorMode[state.get("color_mode", "HUE")]
        self.anim_param_mode = AnimationParamMode.SPEED

        # Set preview_mode based on current mode
        if self.mode == Mode.COLOR_SELECT:
            self.preview_mode = PreviewMode.COLOR_DISPLAY
        elif self.mode == Mode.BRIGHTNESS_ADJUST:
            self.preview_mode = PreviewMode.BAR_INDICATOR
        elif self.mode == Mode.ANIMATION_SELECT:
            self.preview_mode = PreviewMode.ANIMATION_PREVIEW
        elif self.mode == Mode.ANIMATION_PARAM:
            self.preview_mode = PreviewMode.BAR_INDICATOR
        else:
            self.preview_mode = PreviewMode.COLOR_DISPLAY

        # Zone selection
        
        self.zone_names = list(zones.keys())
        self.current_zone_index = 0

        # Parameters per zone (used when not in animation mode)
        self.zone_hues = {z: state["zones"][z]["hue"] for z in self.zone_names}
        self.zone_brightness = {z: state["zones"][z]["brightness"] for z in self.zone_names}
        self.zone_preset_indices = {z: state["zones"][z]["preset"] for z in self.zone_names}

        # Animation system
        self.animation_engine = AnimationEngine(self.strip, zones)

        # Animation state from config
        anim_state = state.get("animation", {})
        self.animation_enabled = anim_state.get("enabled", False)
        self.animation_name = anim_state.get("name", "breathe")
        self.animation_speed = anim_state.get("speed", 50)
        self.animation_color = anim_state.get("color", None)  # None = use zone colors
        self.animation_color2 = anim_state.get("color2", None)
        self.animation_intensity = anim_state.get("intensity", 100)

        # Animation list for selection (ordered)
        self.available_animations = ["breathe", "color_fade", "snake"]
        self.selected_animation_index = 0
        if self.animation_name in self.available_animations:
            self.selected_animation_index = self.available_animations.index(self.animation_name)

        # Pulsing thread for edit mode indicator
        self.pulse_thread = None
        self.pulse_active = False
        self.pulse_lock = asyncio.Lock()

        # Quick lamp state memory (for restoring after quick action)
        self.lamp_saved_state = None  # (hue, preset_idx, brightness, color_mode)

        # Initialize with default colors
        self._initialize_zones()

        # Start pulsing since edit_mode is ON by default
        self._start_pulse()


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

        # Get color based on color_mode
        if self.color_mode == ColorMode.HUE:
            hue = self.zone_hues[zone_name]
            r, g, b = hue_to_rgb(hue)
        else:  # PRESET
            preset_idx = self.zone_preset_indices[zone_name]
            _, (r, g, b) = get_preset_by_index(preset_idx)

        # Apply brightness
        brightness = self.zone_brightness[zone_name]
        scale = brightness / 255.0
        r, g, b = int(r * scale), int(g * scale), int(b * scale)

        self.preview.set_color(r, g, b)

    def _preview_show_bar(self):
        """Preview: Show LED bar (N of 8 LEDs) for numeric value"""
        zone_name = self._get_current_zone()

        # Determine what value to show based on current mode
        if self.mode == Mode.BRIGHTNESS_ADJUST:
            value = self.zone_brightness[zone_name]
            max_value = 255
            color = self._get_zone_color(zone_name)
        elif self.mode == Mode.ANIMATION_PARAM:
            if self.anim_param_mode == AnimationParamMode.SPEED:
                value = self.animation_speed
                max_value = 100
                color = (64, 64, 64)  # Dimmed white bar for speed (25% brightness)
            elif self.anim_param_mode == AnimationParamMode.INTENSITY:
                value = self.animation_intensity
                max_value = 100
                color = (64, 64, 64)  # Dimmed white bar for intensity
            else:
                # For COLOR1/COLOR2, show color instead
                self._preview_show_color()
                return
        else:
            # Fallback to color display
            self._preview_show_color()
            return

        # Calculate how many LEDs to light (0-8)
        num_leds = int((value / max_value) * 8)
        num_leds = max(0, min(8, num_leds))  # Clamp 0-8

        # Set LED bar (right to left, since CJMCU is upside down)
        r, g, b = color
        for i in range(8):
            # Reverse index: 0->7, 1->6, 2->5, etc.
            reversed_i = 7 - i
            if i < num_leds:
                self.preview.strip.setPixelColor(reversed_i, Color(r, g, b))
            else:
                self.preview.strip.setPixelColor(reversed_i, Color(0, 0, 0))
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
        """Get current RGB color for a zone"""
        if self.color_mode == ColorMode.HUE:
            hue = self.zone_hues[zone_name]
            r, g, b = hue_to_rgb(hue)
        else:  # PRESET
            preset_idx = self.zone_preset_indices[zone_name]
            _, (r, g, b) = get_preset_by_index(preset_idx)

        brightness = self.zone_brightness[zone_name]
        scale = brightness / 255.0
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

                # Get base color WITHOUT brightness applied
                if self.color_mode == ColorMode.HUE:
                    hue = self.zone_hues[zone_name]
                    r, g, b = hue_to_rgb(hue)
                else:  # PRESET
                    preset_idx = self.zone_preset_indices[zone_name]
                    _, (r, g, b) = get_preset_by_index(preset_idx)

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
        """Async pulsing animation for current zone"""
        steps = 40

        while self.pulse_active:
            for step in range(steps):
                if not self.pulse_active:
                    break

                # Use animation_speed (1–100) to determine pulse rate dynamically
                speed_factor = max(1, min(100, self.animation_speed))
                cycle_duration = 2.0 - (speed_factor / 50.0)  # 2.0s → 0.0s range
                cycle_duration = max(0.2, cycle_duration)     # prevent too fast flicker
                
                zone_name = self._get_current_zone()
                
                if self.color_mode == ColorMode.HUE:
                    hue = self.zone_hues[zone_name]
                    r, g, b = hue_to_rgb(hue)
                else:  # PRESET
                    preset_idx = self.zone_preset_indices[zone_name]
                    _, (r, g, b) = get_preset_by_index(preset_idx)

                base_brightness = self.zone_brightness[zone_name]

                # smooth sine pulse
                t = step / steps
                brightness_scale = 0.1 + 0.9 * (math.sin(t * 2 * math.pi - math.pi/2) + 1) / 2

                # Apply pulsing brightness
                pulsed_brightness = base_brightness * brightness_scale
                scale = pulsed_brightness / 255.0
                
                #scale = 0.1 + 0.9 * (math.sin(t * 2 * math.pi - math.pi/2) + 1) / 2
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

        # Now switch to new zone, SKIPPING lamp if lamp_solo is active
        for _ in range(len(self.zone_names)):  # Max iterations to avoid infinite loop
            self.current_zone_index = (self.current_zone_index + delta) % len(self.zone_names)
            zone_name = self._get_current_zone()

            # Skip lamp if lamp_solo is ON
            if zone_name == "lamp" and self.lamp_solo:
                continue  # Try next zone
            else:
                break  # Found valid zone

        # Pulsing thread will automatically pick up the new zone (no restart needed)

        # Sync preview
        self._sync_preview()

        # Print feedback
        hue = self.zone_hues[zone_name]
        brightness = self.zone_brightness[zone_name]
        print(f"\n>>> Zone: {zone_name}")
        print(f"    Hue: {hue}°, Brightness: {brightness}/255")

    def adjust_color(self, delta):
        """
        Adjust color for current zone (only in COLOR_SELECT mode)
        Behavior depends on color_mode (HUE or PRESET)

        Args:
            delta: Change amount (degrees for HUE, steps for PRESET)
        """
        if self.mode != Mode.COLOR_SELECT:
            return

        if not self.edit_mode:
            return

        zone_name = self._get_current_zone()

        if self.color_mode == ColorMode.HUE:
            # Smooth hue adjustment
            self.zone_hues[zone_name] = (self.zone_hues[zone_name] + delta) % 360
            hue = self.zone_hues[zone_name]
            r, g, b = hue_to_rgb(hue)
            print(f">>> {zone_name}: Hue = {hue}° (RGB: {r}, {g}, {b})")
        else:  # PRESET
            # Jump between presets
            self.zone_preset_indices[zone_name] = (self.zone_preset_indices[zone_name] + delta) % len(PRESET_ORDER)
            preset_idx = self.zone_preset_indices[zone_name]
            preset_name, (r, g, b) = get_preset_by_index(preset_idx)
            print(f">>> {zone_name}: Preset = '{preset_name}' (RGB: {r}, {g}, {b})")

        # Don't manually apply color - pulsing thread will pick it up automatically
        # Only update preview
        self._sync_preview()

    def adjust_brightness(self, delta):
        """
        Adjust brightness for current zone (only in BRIGHTNESS_ADJUST mode)
        8 levels: 0, 32, 64, 96, 128, 160, 192, 224, 255

        Args:
            delta: Change in brightness steps (+1 or -1)
        """
        if self.mode != Mode.BRIGHTNESS_ADJUST:
            return

        if not self.edit_mode:
            return

        zone_name = self._get_current_zone()

        # Current brightness level (0-8)
        current = self.zone_brightness[zone_name]
        current_level = round(current / 32)  # Convert to 0-8 scale

        # Adjust level
        new_level = max(0, min(8, current_level + delta))

        # Convert back to 0-255 (8 levels: 0, 32, 64, 96, 128, 160, 192, 224, 255)
        new_brightness = new_level * 32
        if new_level == 8:
            new_brightness = 255  # Max level = 255, not 256

        self.zone_brightness[zone_name] = new_brightness

        # Don't manually apply brightness - pulsing thread will pick it up automatically
        # Update preview (bar indicator)
        self._sync_preview()

        print(f">>> {zone_name}: Brightness = {new_brightness}/255 (level {new_level}/8)")

    def adjust_animation_speed(self, delta):
        """
        Adjust global animation speed (1–100).
        Called when in ANIMATION_PARAM mode with SPEED submode.
        Updates live if animation is running.
        """
        if self.mode != Mode.ANIMATION_PARAM or self.anim_param_mode != AnimationParamMode.SPEED:
            return

        self.animation_speed = max(1, min(100, self.animation_speed + delta))

        # Update live if animation is running
        if self.animation_enabled:
            self.animation_engine.update_param("speed", self.animation_speed)

        print(f">>> Animation speed = {self.animation_speed}/100")
        self._sync_preview()

    def switch_mode(self):
        """
        Switch between main modes (only when edit_mode=ON)
        COLOR_SELECT -> BRIGHTNESS_ADJUST -> ANIMATION_SELECT -> ANIMATION_PARAM -> (loop)
        """
        if not self.edit_mode:
            print("[INFO] Enter edit mode first to switch modes")
            return

        modes = list(Mode)
        idx = modes.index(self.mode)
        self.mode = modes[(idx + 1) % len(modes)]

        # Update preview_mode based on new mode
        if self.mode == Mode.COLOR_SELECT:
            self.preview_mode = PreviewMode.COLOR_DISPLAY
        elif self.mode == Mode.BRIGHTNESS_ADJUST:
            self.preview_mode = PreviewMode.BAR_INDICATOR
        elif self.mode == Mode.ANIMATION_SELECT:
            self.preview_mode = PreviewMode.ANIMATION_PREVIEW
        elif self.mode == Mode.ANIMATION_PARAM:
            self.preview_mode = PreviewMode.BAR_INDICATOR

        self._sync_preview()
        print(f"\n>>> Mode: {self.mode.name}")

    def toggle_edit_mode(self):
        """Toggle edit mode ON/OFF"""
        self.edit_mode = not self.edit_mode

        if self.edit_mode:
            print(f"\n>>> EDIT MODE: ON")
            print(f"    Zone: {self._get_current_zone()}")
            print(f"    Mode: {self.mode.name}")
            self._start_pulse()  # Start pulsing the selected zone
            self._sync_preview()
        else:
            print(f"\n>>> EDIT MODE: OFF")
            self._stop_pulse()  # Stop pulsing and restore color

    def switch_color_submode(self):
        """Switch between HUE and PRESET color modes (only in COLOR_SELECT)"""
        if self.mode != Mode.COLOR_SELECT:
            return

        if self.color_mode == ColorMode.HUE:
            self.color_mode = ColorMode.PRESET
        else:
            self.color_mode = ColorMode.HUE

        print(f"\n>>> Color Mode: {self.color_mode.name}")
        self._sync_preview()

    def switch_anim_param_submode(self):
        """Switch between animation parameter submodes (only in ANIMATION_PARAM)"""
        if self.mode != Mode.ANIMATION_PARAM:
            return

        params = list(AnimationParamMode)
        idx = params.index(self.anim_param_mode)
        self.anim_param_mode = params[(idx + 1) % len(params)]

        print(f"\n>>> Animation Parameter: {self.anim_param_mode.name}")
        self._sync_preview()

    def toggle_lamp_solo(self):
        """Toggle lamp solo mode - IMMEDIATELY saves and activates warm white"""
        if not self.lamp_solo:
            # Activating solo mode: save current lamp state
            self.lamp_solo_state = {
                "hue": self.zone_hues["lamp"],
                "brightness": self.zone_brightness["lamp"],
                "preset": self.zone_preset_indices["lamp"]
            }
            self.lamp_solo = True

            # Set lamp to warm white immediately
            preset_idx = PRESET_ORDER.index("warm_white")
            self.zone_preset_indices["lamp"] = preset_idx
            self.zone_brightness["lamp"] = 255

            # Apply to strip immediately
            _, (r, g, b) = get_preset_by_index(preset_idx)
            self.strip.set_zone_color("lamp", r, g, b)

            print(f"\n>>> LAMP SOLO: ON")
            print("    Lamp -> Warm White @ Full Brightness (state saved)")
        else:
            # Deactivating solo mode: restore previous state
            self.lamp_solo = False

            if self.lamp_solo_state:
                self.zone_hues["lamp"] = self.lamp_solo_state["hue"]
                self.zone_brightness["lamp"] = self.lamp_solo_state["brightness"]
                self.zone_preset_indices["lamp"] = self.lamp_solo_state["preset"]

                # Apply to strip immediately
                r, g, b = self._get_zone_color("lamp")
                self.strip.set_zone_color("lamp", r, g, b)

                print(f"\n>>> LAMP SOLO: OFF")
                print(f"    Lamp restored: brightness={self.lamp_solo_state['brightness']}/255")

                self.lamp_solo_state = None
            else:
                print(f"\n>>> LAMP SOLO: OFF")
                print("    (No saved state to restore)")

    def quick_lamp_white(self):
        """
        Quick action: Toggle lamp between warm white and previous state
        First press: Save current state, set warm white @ full
        Second press: Restore previous state
        """
        if self.lamp_saved_state is None:
            # Save current state and set warm white
            self.lamp_saved_state = (
                self.zone_hues["lamp"],
                self.zone_preset_indices["lamp"],
                self.zone_brightness["lamp"],
                self.color_mode
            )

            # Set to warm white
            preset_idx = PRESET_ORDER.index("warm_white")
            self.zone_preset_indices["lamp"] = preset_idx
            self.zone_brightness["lamp"] = 255

            # Apply to strip immediately
            _, (r, g, b) = get_preset_by_index(preset_idx)
            self.strip.set_zone_color("lamp", r, g, b)

            print("\n>>> QUICK ACTION: Lamp -> Warm White @ Full Brightness")
            print("    (Previous state saved - press again to restore)")
        else:
            # Restore previous state
            hue, preset_idx, brightness, color_mode = self.lamp_saved_state
            self.zone_hues["lamp"] = hue
            self.zone_preset_indices["lamp"] = preset_idx
            self.zone_brightness["lamp"] = brightness
            self.color_mode = color_mode

            # Apply to strip immediately
            r, g, b = self._get_zone_color("lamp")
            self.strip.set_zone_color("lamp", r, g, b)

            self.lamp_saved_state = None  # Clear saved state

            print("\n>>> QUICK ACTION: Lamp -> Previous state restored")
            print(f"    Brightness: {brightness}/255")

    def power_toggle(self):
        """Toggle power for all zones (ON/OFF) - saves and restores brightness"""
        # Check if any zone has brightness > 0
        any_on = any(self.zone_brightness[zone] > 0 for zone in self.zone_names)

        if any_on:
            # Turning OFF: Save current brightness and turn off
            if not hasattr(self, 'power_saved_brightness'):
                self.power_saved_brightness = {}

            for zone in self.zone_names:
                # Save current brightness
                self.power_saved_brightness[zone] = self.zone_brightness[zone]
                # Turn off
                self.zone_brightness[zone] = 0
                self.strip.set_zone_color(zone, 0, 0, 0)

            self.preview.clear()
            print("\n>>> POWER: OFF (brightness saved)")
        else:
            # Turning ON: Restore saved brightness
            if hasattr(self, 'power_saved_brightness') and self.power_saved_brightness:
                # Restore saved brightness
                for zone in self.zone_names:
                    saved = self.power_saved_brightness.get(zone, 64)  # Default 64 if not saved
                    self.zone_brightness[zone] = saved
                    r, g, b = self._get_zone_color(zone)
                    self.strip.set_zone_color(zone, r, g, b)
                print("\n>>> POWER: ON (brightness restored)")
            else:
                # No saved state, use default brightness (64)
                for zone in self.zone_names:
                    self.zone_brightness[zone] = 64
                    r, g, b = self._get_zone_color(zone)
                    self.strip.set_zone_color(zone, r, g, b)
                print("\n>>> POWER: ON (default brightness)")

            self._sync_preview()

    def clear_all(self):
        """Turn off all LEDs"""
        self.strip.clear()
        self.preview.clear()
        print(">>> All LEDs cleared")

    async def start_animation(self):
        """Start the currently selected animation"""
        if self.animation_enabled:
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
                params["start_hue"] = self.zone_hues[zone_name]
        elif self.animation_name == "snake":
            if self.animation_color:
                params["color"] = tuple(self.animation_color)
            else:
                params["color"] = (255, 255, 255)

        # Exclude lamp from animation if lamp_solo is ON
        excluded_zones = ["lamp"] if self.lamp_solo else []

        # Start animation
        await self.animation_engine.start(self.animation_name, excluded_zones=excluded_zones, **params)

        # Cache brightness values for animations
        for zone_name in self.zone_names:
            brightness = self.zone_brightness[zone_name]
            self.animation_engine.current_animation.set_zone_brightness_cache(zone_name, brightness)

        self.animation_enabled = True

        print(f"\n>>> ANIMATION STARTED: {self.animation_name}")
        print(f"    Speed: {self.animation_speed}/100")

    async def stop_animation(self):
        """Stop current animation and restore static colors"""
        if not self.animation_enabled:
            return

        await self.animation_engine.stop()
        self.animation_enabled = False

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

    def get_status(self):
        """
        Get current status

        Returns:
            Dict with current state matching state.json structure
        """
        return {
            "mode": self.mode.name,
            "color_mode": self.color_mode.name,
            "edit_mode": self.edit_mode,
            "lamp_solo": self.lamp_solo,
            "lamp_solo_state": self.lamp_solo_state,
            "animation": {
                "enabled": self.animation_enabled,
                "name": self.animation_name,
                "speed": self.animation_speed,
                "color": self.animation_color,
                "color2": self.animation_color2,
                "intensity": self.animation_intensity
            },
            "zones": {
                zone: {
                    "hue": self.zone_hues[zone],
                    "brightness": self.zone_brightness[zone],
                    "preset": self.zone_preset_indices[zone]
                }
                for zone in self.zone_names
            }
        }

