---
Last Updated: 2025-11-25
Type: Agent Documentation
Purpose: Current hardware configuration, GPIO pins, zones, and pixels
---

# Current Configuration

## Hardware Setup

**Platform**: Raspberry Pi 4 (GPIO-based LED control)
**Total Pixels**: 119 (51 on GPIO 18, 68 on GPIO 19)
**LED Types**: WS2811 (GPIO 18) + WS2812B (GPIO 19)
**Target FPS**: 60 (16.67ms per frame)

## GPIO 18 - Main Strip (12V WS2811)

```
GPIO Pin: 18
LED Type: WS2811
Voltage: 12V
Color Order: BGR (Blue, Green, Red)
Total Pixels: 51
Configuration File: src/config/zones.yaml, src/config/hardware.yaml
```

### Zones on GPIO 18

| Zone ID | Name | Pixels | Indices | Notes |
|---------|------|--------|---------|-------|
| FLOOR | FLOOR | 15 | 0-14 | Large zone, floor LEDs |
| LEFT | LEFT | 10 | 15-24 | Left wall |
| TOP | TOP | 10 | 25-34 | Top area |
| RIGHT | RIGHT | 10 | 35-44 | Right wall |
| BOTTOM | BOTTOM | 5 | 45-49 | Bottom area |
| LAMP | LAMP | 1 | 50 | Single pixel for lamp |

**Total GPIO 18**: 51 pixels across 6 zones

### Pixel Arrangement

```
GPIO 18 DMA Buffer Layout:
[0-14]     [15-24]    [25-34]    [35-44]    [45-49] [50]
 FLOOR      LEFT       TOP        RIGHT     BOTTOM  LAMP
```

**Color Order**: Each pixel stored as BGR bytes
```
Index 0 (FLOOR[0]): [B][G][R] (3 bytes)
Index 1 (FLOOR[1]): [B][G][R] (3 bytes)
...
Index 50 (LAMP):    [B][G][R] (3 bytes)
```

## GPIO 19 - Auxiliary Strip (5V WS2812B)

```
GPIO Pin: 19
LED Type: WS2812B
Voltage: 5V
Color Order: GRB (Green, Red, Blue)
Total Pixels: 68
Configuration File: src/config/zones.yaml, src/config/hardware.yaml
```

### Zones on GPIO 19

| Zone ID | Name | Pixels | Indices | Notes |
|---------|------|--------|---------|-------|
| PIXEL | PIXEL | 1 | 0 | Single test pixel |
| PIXEL2 | PIXEL2 | 1 | 1 | Single test pixel |
| PREVIEW | PREVIEW | 8 | 2-9 | 8-LED preview panel |
| (Spare) | (spare) | 58 | 10-67 | Available for expansion |

**Total GPIO 19**: 68 pixels (10 used, 58 available)

### Pixel Arrangement

```
GPIO 19 DMA Buffer Layout:
[0]     [1]      [2-9]     [10-67]
PIXEL  PIXEL2   PREVIEW    (spare)
```

**Color Order**: Each pixel stored as GRB bytes (different from GPIO 18!)
```
Index 0 (PIXEL):     [G][R][B] (3 bytes)
Index 1 (PIXEL2):    [G][R][B] (3 bytes)
...
Index 9 (PREVIEW):   [G][R][B] (3 bytes)
```

## Multi-GPIO Architecture

### How Zones are Mapped to GPIO

**Configuration Files**:
1. `hardware.yaml` - Defines physical LED strips (GPIO pins, types, counts)
2. `zone_mapping.yaml` - Maps zones to hardware strips (explicit mappings)
3. `zones.yaml` - Defines logical zones (names, pixel counts)

**ConfigManager** (src/managers/config_manager.py:277-308):
```python
# Reads zone_mapping.yaml and hardware.yaml
# Builds GPIO → zones mapping
# Auto-assigns zone.config.gpio property
# Calculates per-GPIO pixel indices
```

**main_asyncio** (src/main_asyncio.py:80-126):
```python
# Groups zones by GPIO pin
zones_by_gpio = {
    18: [FLOOR, LEFT, TOP, RIGHT, BOTTOM, LAMP],
    19: [PIXEL, PIXEL2, PREVIEW]
}

# Creates one WS281xStrip per GPIO
for gpio_pin, zones in zones_by_gpio.items():
    hardware = WS281xStrip(gpio_pin, zones)
    strip = ZoneStrip(zones, hardware)
    frame_manager.add_main_strip(strip)
```

### Critical Detail: Per-GPIO Pixel Indices

**Each GPIO has its own index space starting at 0**:

```
Global perspective:
GPIO 18: [0  ][1  ][2  ]...[50 ]  (indices 0-50 on GPIO 18)
GPIO 19: [0  ][1  ][2  ]...[67 ]  (indices 0-67 on GPIO 19)

NOT: [0-50 on GPIO 18][51-118 on GPIO 19]
```

**Why?**: Each GPIO's hardware operates independently. Pixel indices are per-GPIO, not global.

**Implementation**: ZonePixelMapper handles this (src/zone_layer/zone_pixel_mapper.py)

```python
# Gets pixel indices for zone relative to its GPIO
pixel_indices = mapper.get_zone_pixel_indices(ZoneID.FLOOR)
# Returns: [0, 1, 2, ..., 14]  (0-indexed on GPIO 18)
```

## Configuration Files

### hardware.yaml

Defines physical LED strips:

```yaml
led_strips:
  - id: GPIO_18_MAIN
    gpio: 18
    type: WS2811_12V
    color_order: BGR
    count: 51

  - id: GPIO_19_AUX
    gpio: 19
    type: WS2812_5V
    color_order: GRB
    count: 68
```

### zone_mapping.yaml

Maps zones to hardware strips:

```yaml
hardware_mappings:
  - hardware_id: GPIO_18_MAIN
    zones:
      - FLOOR
      - LEFT
      - TOP
      - RIGHT
      - BOTTOM
      - LAMP

  - hardware_id: GPIO_19_AUX
    zones:
      - PIXEL
      - PIXEL2
      - PREVIEW
```

### zones.yaml

Defines logical zones:

```yaml
zones:
  - id: FLOOR
    name: Floor
    pixel_count: 15
    enabled: true
    # GPIO auto-assigned by ConfigManager!

  - id: LEFT
    name: Left
    pixel_count: 10
    enabled: true

  # ... etc
```

**Key**: No GPIO specified in zones.yaml. ConfigManager auto-assigns based on hardware.yaml and zone_mapping.yaml.

## Frame Rendering Flow

**When a frame is rendered to GPIO 18**:

```
1. ZoneFrame received: {FLOOR: red, LEFT: blue, ...}

2. ZoneStrip processes frame:
   - Get pixels for FLOOR zone: indices [0-14] on GPIO 18
   - Get pixels for LEFT zone: indices [15-24] on GPIO 18
   - ... etc for all zones

3. Build complete pixel array (51 pixels):
   pixels[0:15]   = FLOOR color
   pixels[15:25]  = LEFT color
   pixels[25:35]  = TOP color
   pixels[35:45]  = RIGHT color
   pixels[45:50]  = BOTTOM color
   pixels[50]     = LAMP color

4. Convert colors to RGB (handle brightness):
   for each color:
     r, g, b = color.to_rgb_with_brightness(zone.brightness)

5. Remap to hardware color order (BGR for GPIO 18):
   hardware_pixel[0]   = [B, G, R]  ← Red is now at end
   hardware_pixel[1]   = [B, G, R]
   ... etc

6. Load into DMA buffer:
   WS281xStrip.apply_frame(dma_buffer)

7. Send to hardware:
   WS281xStrip.show()

8. Result: GPIO 18 outputs all 51 pixels to LED strip
```

**Simultaneously for GPIO 19**: Same process, different color order (GRB instead of BGR)

## Pixel Memory Layout

### GPIO 18 Memory (for developer reference)

```
Pixel Index | Zone    | Use | Position in Zone
0           | FLOOR   | 0   | FLOOR[0]
1           | FLOOR   | 1   | FLOOR[1]
...
14          | FLOOR   | 14  | FLOOR[14]
15          | LEFT    | 0   | LEFT[0]
16          | LEFT    | 1   | LEFT[1]
...
24          | LEFT    | 9   | LEFT[9]
25          | TOP     | 0   | TOP[0]
...
34          | TOP     | 9   | TOP[9]
35          | RIGHT   | 0   | RIGHT[0]
...
44          | RIGHT   | 9   | RIGHT[9]
45          | BOTTOM  | 0   | BOTTOM[0]
...
49          | BOTTOM  | 4   | BOTTOM[4]
50          | LAMP    | 0   | LAMP[0]
```

### GPIO 19 Memory

```
Pixel Index | Zone    | Use
0           | PIXEL   | 0
1           | PIXEL2  | 0
2           | PREVIEW | 0
3           | PREVIEW | 1
...
9           | PREVIEW | 7
10-67       | (spare) | (available)
```

## Key Code Locations

### Configuration Loading
- `src/managers/config_manager.py` - Loads configs, assigns GPIO to zones
- `src/managers/config_manager.py:277-308` - Multi-GPIO zone parsing

### Zone Mapping
- `src/zone_layer/zone_pixel_mapper.py` - Converts zone ID to pixel indices
- `src/zone_layer/led_channel.py` - Maintains pixel buffer

### Hardware Initialization
- `src/main_asyncio.py:80-126` - Creates WS281xStrip per GPIO
- `src/hardware/led/ws281x_strip.py` - Hardware layer implementation

### Frame Rendering
- `src/engine/frame_manager.py:433-460` - Renders pixel frames
- `src/zone_layer/led_channel.py:show_full_pixel_frame()` - Submits to hardware

## Adding a New GPIO Pin

**To add GPIO 21 with 100 pixels**:

1. **Update hardware.yaml**:
```yaml
- id: GPIO_21_STRIP
  gpio: 21
  type: WS2812
  color_order: RGB
  count: 100
```

2. **Update zone_mapping.yaml**:
```yaml
- hardware_id: GPIO_21_STRIP
  zones:
    - NEW_ZONE_1
    - NEW_ZONE_2
```

3. **Update zones.yaml**:
```yaml
- id: NEW_ZONE_1
  name: New Zone 1
  pixel_count: 50
  enabled: true
  # GPIO auto-assigned!
```

4. **Restart application** (config loaded at startup)

Result: New GPIO, zones, and hardware integrated automatically. No code changes!

## Performance Metrics

**DMA Transfer Time**:
- GPIO 18 (51 pixels): ~2.25ms
- GPIO 19 (68 pixels): ~2.85ms
- Both: Sequential, total ~5.1ms (still within 16.67ms budget)

**Frame Cycle Time**:
- Target: 16.67ms (60 FPS)
- Used: ~5.1ms (DMA) + ~3ms (processing)
- Headroom: ~8.5ms per cycle

**Memory Usage**:
- GPIO 18 buffer: 51 × 3 bytes = 153 bytes
- GPIO 19 buffer: 68 × 3 bytes = 204 bytes
- Total: 357 bytes (negligible)

## Summary

**Current Hardware**:
- GPIO 18: 51 WS2811 pixels (BGR), 6 zones
- GPIO 19: 68 WS2812B pixels (GRB), 3 zones + spare
- Multi-GPIO support: Each GPIO renders independently
- Per-GPIO pixel indexing: Indices 0-based per GPIO

**Configuration**:
- hardware.yaml: Physical strip definitions
- zone_mapping.yaml: Zone → hardware mapping
- zones.yaml: Logical zone definitions
- ConfigManager: Auto-assigns GPIO to zones

**Architecture**:
- Clean separation of zones and hardware
- Easy to add new GPIO pins
- Type-safe zone handling
- Hardware independence maintained

---

**Next**: [Code Map](2_code_map.md)
