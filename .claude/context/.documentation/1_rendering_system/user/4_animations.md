---
Last Updated: 2025-11-25
Type: User Documentation
Purpose: Understanding animation types, generators, and parameters
---

# Animations

## What is an Animation?

An **animation** is an effect that changes colors over time. Instead of showing a static color, animations produce a sequence of color changes that create visual effects.

### Animation Characteristics

**Generator-Based**:
- Animations are Python async generators
- They yield color values continuously
- System consumes yields and renders each
- Clean separation: animation logic ≠ rendering logic

**Stateful**:
- Animations maintain internal state (time, phase, etc.)
- Each animation instance is independent
- Can run multiple instances simultaneously (different zones)

**Parameterized**:
- Animations accept parameters (speed, intensity, color)
- Parameters can be adjusted during animation
- Changes apply smoothly (no jarring transitions)

**Zone-Independent**:
- Animations don't know which zone they're running on
- Same animation code works on any zone
- Can animate one zone while others stay static

### Animation Lifecycle

```
User starts animation
    ↓
AnimationEngine creates animation instance
    ↓
Async generator function starts
    ↓
Generator yields color values (continuously)
    ↓
System consumes each yield
    ↓
Converts yield to frame object
    ↓
Submits frame to FrameManager with ANIMATION priority
    ↓
FrameManager renders frame
    ↓
LEDs display animation
    ↓
[Repeat yield → frame → render cycle]
    ↓
User stops animation
    ↓
Generator stops cleanly
    ↓
Next frame submitted, animation exits
```

## Animation Types

### Type 1: Breathe (Zone-Based)

**What it does**: Zone color pulses in and out, like breathing

**Parameters**:
- `speed`: How fast to pulse (0.5-2.0x normal speed)
- `intensity`: How bright at peak (0.5-1.0 scale)
- `primary_color`: Color to breathe

**Visual effect**:
```
Time:  0ms    250ms    500ms   750ms   1000ms
       dark    ↗ bright  ↘ dark  ↗ bright ↘
       ■       ███       ■       ███       ■
```

**Yields**: `(zone_id, Color)` - same color with varying brightness

---

### Type 2: Color Fade (Zone-Based)

**What it does**: Smoothly fades from one color to another

**Parameters**:
- `speed`: Fade duration and cycle speed
- `primary_color`: Starting color
- `secondary_color`: Ending color (if supported)

**Visual effect**:
```
Red → Orange → Yellow → Orange → Red (cycles)
```

**Yields**: `(zone_id, Color)` - interpolated between colors

---

### Type 3: Snake (Pixel-Based)

**What it does**: Animated pixel that moves across the zone

**Parameters**:
- `speed`: How fast the pixel moves
- `intensity`: Pixel brightness
- `primary_color`: Pixel color
- `length`: How many pixels form the snake body

**Visual effect**:
```
Zone pixels: [■ ■ ■ ■ ■ ■ ■ ■ ■ ■]
             [⚪ ◐ ◑ ◒ ■ ■ ■ ■ ■ ■] (bright moving dot)
             [■ ⚪ ◐ ◑ ◒ ■ ■ ■ ■ ■] (moves right)
```

**Yields**: `(zone_id, pixel_index, Color)` - individual pixels

---

### Type 4: Color Snake (Pixel-Based)

**What it does**: Multi-color snake that moves across zone

**Parameters**:
- `speed`: How fast the snake moves
- `primary_color`: First color in snake
- `secondary_color`: Second color in snake
- `length`: Snake body length

**Visual effect**:
```
[Red⚪ ◐ Blue ◑ Red ■ ■ ■ ■ ■]
[■ Red⚪ ◐ Blue ◑ Red ■ ■ ■ ■]
```

**Yields**: `(zone_id, pixel_index, Color)` - individual pixels with color

---

### Type 5: Color Cycle (Full-Strip)

**What it does**: Rotates through entire color wheel

**Parameters**:
- `speed`: How fast to cycle
- `intensity`: Brightness level

**Visual effect**:
```
All zones: Red
All zones: Orange
All zones: Yellow
All zones: Green
...
```

**Yields**: `(Color)` - single color for all pixels

---

### Type 6: Rainbow (Full-Strip)

**What it does**: Creates rainbow spectrum across all zones

**Parameters**:
- `speed`: How fast the rainbow shifts
- `intensity`: Rainbow brightness

**Visual effect**:
```
Zone 1:    Zone 2:    Zone 3:    ...
Red        Orange     Yellow     Green ...
```

**Yields**: `(Color)` - array of colors for all pixels

---

### Type 7: Pulse (Zone-Based)

**What it does**: Simple on/off pulse effect

**Parameters**:
- `speed`: Pulse frequency
- `primary_color`: Pulse color

**Visual effect**:
```
On    Off    On    Off    On
███   ■      ███   ■      ███
```

**Yields**: `(zone_id, Color)` - alternates between color and black

---

### Type 8: Strobe (Zone-Based)

**What it does**: Rapid flash effect

**Parameters**:
- `speed`: Flash frequency
- `intensity`: Flash brightness
- `primary_color`: Flash color

**Visual effect**:
```
Flash On    (2ms)
Flash Off   (2ms)
Flash On    (2ms)
...
```

**Yields**: `(zone_id, Color)` - fast on/off cycle

---

### Type 9: Wave (Pixel-Based)

**What it does**: Wave pattern rippling across pixels

**Parameters**:
- `speed`: Wave speed
- `intensity`: Wave brightness
- `primary_color`: Wave color
- `wavelength`: Distance between wave peaks

**Visual effect**:
```
[⚪ ◐ ◑ ◒ ■ ■ ■ ■ ■ ■]
[■ ⚪ ◐ ◑ ◒ ■ ■ ■ ■ ■]
[■ ■ ⚪ ◐ ◑ ◒ ■ ■ ■ ■]
```

**Yields**: `(zone_id, pixel_index, Color)` - wave envelope across zone

---

## Animation Generators Explained

### What is an Async Generator?

```python
# Simple animation generator
async def breathe_animation(zone_id, speed, color):
    while True:  # Run forever
        # Compute brightness based on time
        brightness = compute_sine_wave(speed)

        # Adjust color brightness
        pulsing_color = color.with_brightness(brightness)

        # Yield the color for this frame
        yield (zone_id, pulsing_color)

        # Wait before next frame (60 FPS)
        await asyncio.sleep(1/60)
```

### Generator Patterns

**Zone-Based Pattern** (most common):
```python
async def zone_animation(zone_id, speed, color):
    while True:
        new_color = compute_color(speed, color)
        yield (zone_id, new_color)  # Entire zone same color
        await asyncio.sleep(1/60)
```

**Pixel-Based Pattern**:
```python
async def pixel_animation(zone_id, speed, color, zone_pixel_count):
    while True:
        for pixel_idx in range(zone_pixel_count):
            pixel_color = compute_color_for_pixel(pixel_idx, speed, color)
            yield (zone_id, pixel_idx, pixel_color)  # Individual pixel
        await asyncio.sleep(1/60)
```

**Full-Strip Pattern**:
```python
async def strip_animation(speed, color):
    while True:
        all_colors = compute_colors_for_all_zones(speed, color)
        yield all_colors  # All zones at once
        await asyncio.sleep(1/60)
```

### Why Generators?

**Advantages**:
- **Lazy evaluation**: Only computes next frame when needed
- **Infinite loops**: Natural for continuous effects
- **Memory efficient**: No storage of all frames upfront
- **Clean code**: Animation logic separate from rendering
- **Pausable**: Generator can be paused/resumed

**Alternative approach** (not used):
```python
# Bad: Precompute all frames in advance
frames = []
for i in range(10000):  # 10000 frames
    frames.append(compute_frame(i))  # Big memory usage!

# Then render them
for frame in frames:
    render(frame)
```

**Generator approach** (used):
```python
# Good: Compute on-demand
async def animation():
    i = 0
    while True:
        frame = compute_frame(i)  # Just this frame
        yield frame  # Send to renderer
        i += 1
        await asyncio.sleep(1/60)
```

---

## Animation Parameters

### Standard Parameters

**All animations support**:

`speed` (1-100):
- How fast the effect animates
- 1 = slow (half speed)
- 50 = normal (1x speed)
- 100 = fast (2x speed)

`intensity` (0-100):
- Brightness/prominence of effect
- 0 = barely visible
- 50 = normal
- 100 = maximum brightness

`primary_color`:
- Main color of animation
- Used by most animations
- Can be adjusted during animation

### Optional Parameters

`secondary_color`:
- Second color for multi-color animations
- Used by Color Fade, Color Snake, etc.
- Optional (defaults to black or primary)

`wavelength`:
- For wave-based animations
- Distance between wave peaks
- Affects visual "tightness" of waves

`length`:
- For snake-based animations
- How many pixels form the snake body
- Affects "tail" effect

### Parameter Adjustment

**During animation**:
```python
# Animation running with speed=50
animation_engine.update_parameter('speed', 75)  # Speeds up
animation_engine.update_parameter('primary_color', Color.new(...))  # Color changes
```

**Changes are smooth**:
- No stuttering or jarring jumps
- Updated parameter used in next frame
- Animation continues flowing

---

## Animation Execution Flow

**Complete example**:

```
1. User presses button to start "BREATHE" animation on selected zone (FLOOR)
   ↓
2. LEDController routes to AnimationModeController
   ↓
3. AnimationModeController calls:
   animation_engine.start('BREATHE', excluded_zones=[...], speed=50, color=red)
   ↓
4. AnimationEngine:
   - Creates animation instance
   - Builds list of excluded zones (all except selected)
   - Starts _run_loop() task
   ↓
5. _run_loop() task:
   while animation_running:
     frame = await animation_generator.asend(None)
     # frame is (zone_id, Color)

     # Convert to frame object
     zone_frame = ZoneFrame(
       zones={zone_id: frame.color},
       priority=ANIMATION
     )

     # Submit to FrameManager
     await frame_manager.submit_zone_frame(zone_frame)

     # Wait for next frame timing
     await frame_manager.wait_render_cycle()
   ↓
6. FrameManager render loop (60 FPS):
   for each cycle:
     selected_frame = select_highest_priority_frame()

     if is_zone_frame(selected_frame):
       render_zone_frame(selected_frame)

     zone_strip.show()
   ↓
7. Result:
   - FLOOR zone displays breathing animation
   - Other zones display their static colors
   - Animation continues until user stops it
```

---

## Summary

**Animations are**:
- Async generators (infinite loops yielding frames)
- Parameterized (speed, intensity, colors)
- Zone-independent (same code on any zone)
- Efficient (lazy, on-demand computation)
- Smooth (transitions between effects)

**Types include**:
- Zone-based (Breathe, Color Fade, Pulse, Strobe)
- Pixel-based (Snake, Color Snake, Wave)
- Full-strip (Color Cycle, Rainbow)

**System handles**:
- Lifecycle (start/stop with transitions)
- Parameter updates (smooth changes)
- Zone exclusion (animate selected, preserve others)
- Frame submission (priority system)
- Rendering (60 FPS target)

**You control**:
- Which animation to run
- Parameters (speed, intensity, color)
- Which zone to animate
- When to start/stop

---

**Next:** [Frame Priority System](5_frame_priority_system.md)
