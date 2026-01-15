---
Last Updated: 2025-11-25
Type: User Documentation
Purpose: Understanding hardware independence and Color class
---

# Hardware Abstraction

## The Hardware Independence Goal

The Diuna system is completely **hardware-independent**. This means:
- Animation code never mentions GPIO pins, pixel counts, or hardware types
- Controllers work with abstract concepts (zones, colors)
- The same code can run on different hardware setups
- Hardware changes don't require application logic changes

This is achieved through two key design patterns:

1. **IPhysicalStrip Interface**: Hide hardware details
2. **Color Class**: Standardize color representation

## IPhysicalStrip Interface

The `IPhysicalStrip` interface defines the minimal contract that any LED strip hardware must implement:

```python
class IPhysicalStrip(Protocol):
    def apply_frame(self, pixel_array: NDArray) -> None:
        """Load frame into DMA buffer (no hardware update yet)"""
        ...

    def show(self) -> None:
        """DMA transfer to hardware (atomic update)"""
        ...
```

### Why This Design?

**Separation of Concerns**:
- `apply_frame()`: Load data into buffer (software operation)
- `show()`: Send to hardware (hardware operation)
- Separate calls enable atomic rendering (load all data, then show once)

**Hardware Variations**:
- Different LED types (WS2811, WS2812B, APA102, etc.)
- Different GPIO pins (GPIO 18, 19, 21, etc.)
- Different color orders (RGB, BGR, GRB, etc.)
- Different protocols (DMA, SPI, I2C, bit-banging, etc.)

**But interface stays the same**: `apply_frame()` and `show()`.

### Color Order Handling

Different hardware has different color byte orders. For example:
- WS2811 LEDs expect: Blue, Green, Red (BGR)
- WS2812B LEDs expect: Green, Red, Blue (GRB)
- APA102 LEDs expect: Red, Green, Blue (RGB)

**The Solution**: Color order remapping happens ONLY in the hardware layer.

**Application code**:
```python
# Works with logical RGB order always
color = Color(red=255, green=100, blue=50)
```

**Hardware layer** (only place that touches hardware):
```python
# WS2811 needs BGR order
pixel_bytes = [color.blue, color.green, color.red]
dma_buffer[index] = pixel_bytes
```

Result: **Application is completely unaware of color order**. The hardware layer handles it.

## The Color Class

Colors in Diuna are **first-class domain objects**, not just RGB tuples.

### Why not just use tuples or lists?

Tuples `(255, 100, 50)` are problematic because:
- No semantic meaning (is it RGB? BGR? HSV?)
- Easy to pass wrong order accidentally
- Can't add metadata (brightness adjustment, etc.)
- Can't have smart conversions

### Color Class Features

**Creation**:
```python
from models.domain.color import Color

# From RGB (0-255 range)
c1 = Color(red=255, green=100, blue=50)

# From HSV (if supported)
c2 = Color.from_hsv(hue=30, saturation=100, value=100)

# From preset name (if configured)
c3 = Color.from_preset('red')

# Copy with modifications
c4 = c1.with_brightness(0.5)  # 50% brightness
```

**Properties**:
```python
color = Color(red=255, green=100, blue=50)

# Access components
print(color.red)       # 255
print(color.green)     # 100
print(color.blue)      # 50

# Check properties
print(color.is_black)  # False
print(color.brightness_ratio)  # Computed from RGB values
```

**Conversions**:
```python
# To RGB (normalized 0.0-1.0)
r, g, b = color.to_rgb_normalized()

# To RGB with brightness adjustment
r, g, b = color.to_rgb_with_brightness(brightness=0.8)

# To string representations
hex_string = color.to_hex()      # '#FF6432'
tuple_repr = color.to_tuple()    # (255, 100, 50)
```

### Color Throughout the System

**Zones use Color objects**:
```python
zone.set_color(Color(red=255, green=0, blue=0))
```

**Animations work with Color**:
```python
# Animation yields color objects, not bytes
yield (zone_id, Color(red=255, green=100, blue=50))
```

**Transitions use Color**:
```python
# Crossfade from one color to another
await transition_service.crossfade(
    from_color=Color.black(),
    to_color=Color(red=255, green=100, blue=50)
)
```

**Controllers manipulate Color**:
```python
# Adjust hue
new_color = old_color.with_hue_adjustment(delta=15)

# Adjust brightness
dim_color = old_color.with_brightness(0.5)
```

**Only hardware layer converts to bytes**:
```python
# Deep in hardware layer, far from application logic
r, g, b = color.to_rgb_with_brightness(zone.brightness)
hardware_pixel = [b, g, r]  # BGR order for this hardware
```

## Hardware Independence in Practice

### Example: Two Different LED Setups

**Setup 1**: WS2811 on GPIO 18 (BGR, 51 pixels) + WS2812B on GPIO 19 (GRB, 68 pixels)

**Setup 2**: APA102 on GPIO 10 (RGB, 100 pixels)

**The application code is identical** for both setups because:
- It works with Zone abstractions, not pixel details
- It works with Color objects, not byte arrays
- Color order handling is done by hardware layer
- Pixel count is handled by zone mapping

**Only configuration files change**:
- `zones.yaml`: Define logical zones (same for any setup)
- `hardware.yaml`: Define hardware specifics (different per setup)
- `zone_mapping.yaml`: Map zones to hardware (different per setup)

---

## The Conversion Path

Here's the complete conversion path from application concept to hardware bytes:

```
Application: "Set FLOOR zone to red"
    ↓
State: FLOOR zone has Color(255, 0, 0)
    ↓
Animation/Static generates: ZoneFrame with zone colors
    ↓
FrameManager selects frame, passes to ZoneStrip
    ↓
ZoneStrip gets: {zone_id: Color(255, 0, 0), ...}
    ↓
Zone mapper: "FLOOR zone spans pixel indices 0-14"
    ↓
Create pixel array: pixels[0:15] = Color(255, 0, 0)
    ↓
Hardware layer gets color array
    ↓
Check hardware color order (BGR for GPIO 18)
    ↓
Convert each color:
  Color(255, 0, 0) → (r=255, g=0, b=0)
  Apply brightness: (r=204, g=0, b=0)
  Reorder to BGR: [0, 0, 204]  # BGR bytes
    ↓
Load into DMA buffer
    ↓
DMA transfer: bits → GPIO 18 → LED strip
    ↓
Result: Red light (LED displays red)
```

**Key insight**: The conversion to hardware bytes happens at the absolute last moment, in the deepest layer. Everything above that layer uses domain objects (Colors, Zones).

---

## Benefits of This Approach

### For New Features
Adding a feature doesn't require knowing hardware details:
```python
# Animations don't mention hardware
async def breathe_animation(selected_zone, speed, color):
    while True:
        brightness = compute_sine_wave()
        color_adjusted = color.with_brightness(brightness)
        yield (selected_zone, color_adjusted)
        await asyncio.sleep(1/60)
```

### For Testing
Testing doesn't require hardware:
```python
# Mock the hardware layer
mock_hardware = Mock(spec=IPhysicalStrip)

# Create zone strip with mock
led_channel = ZoneStrip(zones=zones, hardware=mock_hardware)

# Test application logic without GPIO access
animation_service.start('BREATHE')
# ... assertions on mock_hardware calls
```

### For Hardware Changes
Swapping hardware only requires changing the hardware layer:
```python
# Old: WS2811 strips
hardware = WS281xStrip(gpio=18, pixel_count=51, color_order=ColorOrder.BGR)

# New: Different hardware
hardware = MySuperNewLEDDriver(gpio=20, pixel_count=100)

# Rest of code: unchanged!
led_channel = ZoneStrip(zones=zones, hardware=hardware)
```

### For Extension
Adding new animation types is straightforward:
```python
# New animation doesn't need to know:
# - How many zones exist
# - What hardware is running
# - How colors are stored
# - Any other implementation details

async def new_rainbow_animation(selected_zone, speed):
    while True:
        for hue in range(360):
            color = Color.from_hsv(hue=hue, saturation=100, value=100)
            yield (selected_zone, color)
            await asyncio.sleep(0.01 / speed)
```

---

## Summary

The hardware abstraction layer enables:
1. **Hardware Independence**: Change hardware without changing application
2. **Type Safety**: Colors can't be confused with pixels or indices
3. **Testability**: No GPIO required for testing
4. **Extensibility**: Easy to add features, animations, hardware types
5. **Clarity**: Code reads at the correct abstraction level

**Central Principle**: Work with what makes sense at each level. Colors and zones at application level, hardware bytes at hardware level.

---

**Next:** [Zones and Colors](3_zones_and_colors.md)