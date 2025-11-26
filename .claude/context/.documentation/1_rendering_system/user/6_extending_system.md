---
Last Updated: 2025-11-25
Type: User Documentation
Purpose: How to extend the system with new animations, modes, and features
---

# Extending the System

## Overview

The rendering system is designed for extensibility. Adding new features typically means:
1. Implementing a new animation (most common)
2. Adding a new mode or effect type
3. Integrating new hardware
4. Creating new transitions

This guide shows how to do each.

## Adding a New Animation

### Step 1: Understand the Pattern

All animations are async generators that yield color values:

```python
async def my_animation(selected_zone, speed, color, **kwargs):
    """
    Animation generator.

    Args:
        selected_zone: ZoneID of the zone to animate
        speed: Speed parameter (0-100)
        color: Primary color for animation
        **kwargs: Other parameters (intensity, secondary_color, etc.)

    Yields:
        Tuples for rendering:
        - Zone-based: (zone_id, Color)
        - Pixel-based: (zone_id, pixel_index, Color)
        - Full-strip: (Color,) or Color array
    """
    while True:
        # Compute frame based on time, speed, parameters
        current_frame = compute_animation_frame(speed, color)

        # Yield the frame
        yield (selected_zone, current_frame)

        # Wait for next frame (60 FPS target)
        await asyncio.sleep(1/60)
```

### Step 2: Choose Animation Type

**Zone-based** (simplest, most common):
```python
async def my_zone_animation(selected_zone, speed, color):
    while True:
        brightness = compute_brightness(speed)
        adjusted_color = color.with_brightness(brightness)
        yield (selected_zone, adjusted_color)
        await asyncio.sleep(1/60)
```

**Pixel-based** (per-pixel control):
```python
async def my_pixel_animation(selected_zone, speed, color, zone_pixel_count):
    while True:
        for pixel_idx in range(zone_pixel_count):
            pixel_color = compute_pixel_color(pixel_idx, speed, color)
            yield (selected_zone, pixel_idx, pixel_color)
        await asyncio.sleep(1/60)
```

**Full-strip** (all zones at once):
```python
async def my_strip_animation(speed, color):
    while True:
        all_colors = compute_all_colors(speed, color)
        yield all_colors  # dict of zone_id -> Color
        await asyncio.sleep(1/60)
```

### Step 3: Implement the Animation

Example: Custom "Fade Pulse" animation

```python
import asyncio
import math
from models.domain.color import Color
from models.domain.zone import ZoneID

async def fade_pulse_animation(
    selected_zone: ZoneID,
    speed: int = 50,
    color: Color = None,
    intensity: int = 100,
    **kwargs
):
    """
    Pulses color with smooth fade in and out.

    Parameters:
        speed: Pulse speed (faster = more cycles per second)
        color: Color to pulse
        intensity: Peak brightness (0-100)
    """
    if color is None:
        color = Color(red=255, green=0, blue=0)

    cycle_time = 1.0 / (speed / 50.0)  # Normalize speed
    start_time = asyncio.get_event_loop().time()

    while True:
        # Compute time since start
        elapsed = asyncio.get_event_loop().time() - start_time

        # Use sine wave for smooth pulsing
        phase = (elapsed / cycle_time) % 1.0
        brightness = (math.sin(phase * 2 * math.pi) + 1) / 2

        # Apply intensity parameter
        brightness *= (intensity / 100.0)

        # Create pulsing color
        pulsing_color = color.with_brightness(brightness)

        # Yield for rendering
        yield (selected_zone, pulsing_color)

        # Wait for next frame
        await asyncio.sleep(1/60)
```

### Step 4: Register the Animation

**Add to AnimationRegistry** (wherever animations are registered):

```python
from models.enums import AnimationID

# In animation initialization code:
ANIMATION_REGISTRY = {
    AnimationID.BREATHE: breathe_animation,
    AnimationID.SNAKE: snake_animation,
    # Add new animation:
    AnimationID.FADE_PULSE: fade_pulse_animation,
}
```

### Step 5: Add Animation Metadata

**Animations need metadata** (name, description, parameters):

```python
ANIMATION_METADATA = {
    AnimationID.FADE_PULSE: {
        "name": "Fade Pulse",
        "description": "Smooth pulsing effect with customizable intensity",
        "parameters": {
            "speed": {
                "type": "int",
                "min": 1,
                "max": 100,
                "default": 50,
                "description": "Pulse speed"
            },
            "intensity": {
                "type": "int",
                "min": 0,
                "max": 100,
                "default": 100,
                "description": "Peak brightness"
            },
            "primary_color": {
                "type": "Color",
                "default": Color.red(),
                "description": "Pulse color"
            }
        }
    }
}
```

## Adding a New Controller/Mode

### When You Need a New Mode

A new mode is needed when:
- Users interact with LEDs in fundamentally different way
- New user input type (new button, sensor, etc.)
- New rendering strategy (not animation, not static)

### Example: Custom "Temperature" Mode

```python
from controllers.base_controller import BaseController
from models.domain.color import Color
from models.enums import ZoneRenderMode
from services.event_bus import EventBus

class TemperatureModeController(BaseController):
    """
    Control LED color based on temperature sensor input.
    Hotter = more red, cooler = more blue.
    """

    def __init__(self, temperature_sensor, zone_strip_controller, event_bus):
        self.temperature_sensor = temperature_sensor
        self.zone_strip_controller = zone_strip_controller
        self.event_bus = event_bus
        self.running = False

    async def start(self, zone_id):
        """Start temperature mode for a zone."""
        self.running = True
        await self._monitor_temperature(zone_id)

    async def stop(self):
        """Stop temperature mode."""
        self.running = False

    async def _monitor_temperature(self, zone_id):
        """Monitor temperature and update zone color."""
        while self.running:
            # Read temperature
            temp_celsius = await self.temperature_sensor.read()

            # Convert to color (0°C = blue, 100°C = red)
            hue = 240 - (temp_celsius / 100) * 240  # 240° to 0° (blue to red)
            color = Color.from_hsv(hue=hue, saturation=100, value=100)

            # Submit frame
            zone_colors = {zone_id: color}
            frame = ZoneFrame(zones=zone_colors, priority=MANUAL)
            await self.zone_strip_controller.frame_manager.submit_zone_frame(frame)

            # Update ~10 times per second
            await asyncio.sleep(0.1)
```

## Adding New Hardware

### Support a New LED Type

1. **Implement IPhysicalStrip interface**:

```python
class MyCustomLEDDriver:
    """Driver for custom LED hardware."""

    def __init__(self, gpio_pin, pixel_count, color_order):
        self.gpio_pin = gpio_pin
        self.pixel_count = pixel_count
        self.color_order = color_order
        self.buffer = bytearray(pixel_count * 3)

    def apply_frame(self, pixel_array):
        """Load frame into buffer."""
        for i, color in enumerate(pixel_array):
            r, g, b = color.to_rgb()

            # Remap color order based on hardware
            if self.color_order == ColorOrder.RGB:
                self.buffer[i*3:i*3+3] = [r, g, b]
            elif self.color_order == ColorOrder.BGR:
                self.buffer[i*3:i*3+3] = [b, g, r]
            # ... etc

    def show(self):
        """Send buffer to hardware."""
        # Hardware-specific: write buffer to GPIO/SPI/I2C
        self._send_to_hardware(self.buffer)

    def _send_to_hardware(self, data):
        """Implementation-specific hardware communication."""
        # Your implementation here
        pass
```

2. **Use in main application**:

```python
# In main_asyncio.py or equivalent
hardware = MyCustomLEDDriver(
    gpio_pin=21,
    pixel_count=100,
    color_order=ColorOrder.GRB
)

zone_strip = ZoneStrip(
    zones=zone_configs,
    hardware=hardware
)

frame_manager.add_main_strip(zone_strip)
```

**Result**: Everything else unchanged. New hardware integrated seamlessly.

## Adding New Transitions

### Example: Custom "Spiral" Transition

```python
async def spiral_transition(
    from_frame: ZoneFrame,
    to_frame: ZoneFrame,
    duration_ms: int = 500,
    zone_service: ZoneService = None
):
    """
    Transition where color spirals through zones.
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        if elapsed_ms >= duration_ms:
            # Transition complete
            return

        # Compute spiral progress (0.0 to 1.0)
        progress = elapsed_ms / duration_ms

        # For each zone, compute interpolated color
        transition_colors = {}
        for zone in zone_service.get_all():
            # Spiral effect: color ripples through zones
            zone_delay = (zone.config.id * 0.1) % 1.0
            spiral_progress = (progress + zone_delay) % 1.0

            # Interpolate from -> to based on spiral progress
            from_color = from_frame.zones.get(zone.config.id)
            to_color = to_frame.zones.get(zone.config.id)

            if from_color and to_color:
                # Linear interpolation
                t = spiral_progress
                r = int(from_color.red * (1-t) + to_color.red * t)
                g = int(from_color.green * (1-t) + to_color.green * t)
                b = int(from_color.blue * (1-t) + to_color.blue * t)
                transition_colors[zone.config.id] = Color(r, g, b)

        # Submit transition frame
        frame = ZoneFrame(zones=transition_colors, priority=TRANSITION)
        await frame_manager.submit_zone_frame(frame)

        # Wait for next frame
        await asyncio.sleep(1/60)
```

## Adding New Features

### General Pattern

1. **Identify the layer** where feature belongs
   - Hardware detail? → Layer 1 (hardware abstraction)
   - Zone mapping? → Layer 2 (zone layer)
   - Frame selection? → Layer 3 (engine)
   - Animation logic? → Layer 4 (animation)
   - Transition? → Layer 5 (transitions)
   - User interaction? → Layer 6 (controllers)

2. **Implement at appropriate layer**
   - Use layers above (never violate layering)
   - Don't depend on layers below on unnecessary

3. **Submit frames to FrameManager**
   - Never call hardware directly
   - Always use the frame submission pattern

4. **Follow the type system**
   - Use Color objects, not tuples
   - Use ZoneID enums, not strings
   - Use proper type hints

5. **Test independently**
   - Mock dependencies
   - Test without hardware
   - Test at appropriate layer

## Common Extension Scenarios

### Scenario 1: Respond to Temperature Sensor

1. Create service that reads temperature
2. Convert to color using HSV
3. Submit ZoneFrame with MANUAL priority
4. No changes to animation engine, FrameManager, etc.

### Scenario 2: New Visual Effect

1. Implement as animation generator
2. Register in AnimationRegistry
3. Use existing AnimationModeController
4. No changes to rest of system

### Scenario 3: New Hardware Type

1. Implement IPhysicalStrip interface
2. Create instance in main_asyncio
3. Register with FrameManager
4. Application code unchanged

### Scenario 4: New User Input Type

1. Create controller for input source
2. Submit frames based on input
3. Or publish events via EventBus
4. Handle events in existing controllers

### Scenario 5: New Display Mode

1. Create ModeController
2. Integrate with LEDController routing
3. Submit frames via standard pattern
4. Use existing FrameManager priority system

## Best Practices

### DO:
- ✅ Work with Color objects (never RGB tuples)
- ✅ Submit frames to FrameManager (never call hardware)
- ✅ Use type hints throughout
- ✅ Implement at correct architectural layer
- ✅ Test independently with mocks
- ✅ Follow existing naming conventions
- ✅ Keep animations as pure generators

### DON'T:
- ❌ Touch hardware directly (not IPhysicalStrip)
- ❌ Pass pixel indices to high-level code
- ❌ Use magic strings instead of enums
- ❌ Create circular dependencies
- ❌ Block async code with sleep() (use await asyncio.sleep())
- ❌ Assume specific zone counts in code
- ❌ Modify other components' state directly

## Summary

**Extend by**:
1. Adding animations (most common)
2. Creating new modes/controllers
3. Implementing new hardware drivers
4. Building custom transitions
5. Responding to sensors/events

**Key principles**:
- Follow the 6-layer architecture
- Use the frame submission pattern
- Work with domain objects (Colors, Zones)
- Don't violate layer boundaries
- Test with mocks

**Result**: Flexible, maintainable, extensible system.

---

**Documentation Complete**: You now understand how the rendering system works and how to extend it!

For detailed implementation examples and specific code locations, see the [Agent Documentation](../agent/0_agent_overview.md).
