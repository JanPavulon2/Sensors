---
Last Updated: 2025-11-25
Type: User Documentation
Purpose: Understanding zones, per-zone modes, and color handling
---

# Zones and Colors

## What is a Zone?

A **zone** is a logical grouping of LEDs that can be controlled together. Instead of thinking about individual pixels, you think about semantic areas:
- "I want to change the FLOOR zone to red"
- "I want to run an animation on the LEFT zone"
- "I want to dim the LAMP zone"

### Zone Concepts

**Zones are independent**:
- Changing FLOOR color doesn't affect LEFT
- Each zone has its own color, brightness, and mode
- Zones can run different animations simultaneously

**Zones are stateful**:
- Current color (what's displayed now)
- Brightness level (individual zone brightness)
- Enabled/disabled status
- Current mode (STATIC or ANIMATION)

**Zones have geometry**:
- Each zone maps to a range of physical pixels
- Some zones might be reversed (pixels rendered backwards)
- Zone sizes can vary (10 pixels vs 50 pixels)

### Zone Modes

Each zone can independently be in different modes:

**STATIC Mode**:
- Zone displays a fixed color
- User can edit the color using knobs/buttons
- Color persists until changed
- Zone can pulse (edit mode effect)
- Rendered with priority 10 (MANUAL)

**ANIMATION Mode**:
- Zone displays an animated effect
- Parameters (speed, intensity, color) adjustable
- Animation runs continuously
- When selected zone switches to animation, other zones stay static
- Rendered with priority 30 (ANIMATION)

**OFF Mode**:
- Zone is disabled, shows no light
- Still part of system but not rendered
- Can be turned back on

### Why Per-Zone Modes Matter

This architecture enables sophisticated behaviors:

```
Scenario 1: FLOOR running rainbow animation, LAMP static white
├─ FLOOR zone mode: ANIMATION
└─ LAMP zone mode: STATIC

Scenario 2: Pulsing effect on FLOOR (editing), other zones unchanged
├─ FLOOR zone: STATIC mode with pulse effect (priority 20)
└─ Other zones: Continue their modes

Scenario 3: Power fade-out from current state
├─ Current state preserved (animation/static)
└─ Transition overlays FADE priority (40) over everything
```

## Color Handling

### Color Objects

Colors are represented as domain objects throughout the system:

**Creating colors**:
```python
# From RGB values (0-255 each)
from models.domain.color import Color
red = Color(red=255, green=0, blue=0)

# From HSV (if needed)
rainbow = Color.from_hsv(hue=45, saturation=100, value=100)

# From presets (configuration-defined)
warm_white = Color.from_preset('warm_white')

# Creating variations
darker_red = red.with_brightness(0.5)
shifted_hue = red.with_hue_adjustment(30)
```

**Comparing colors**:
```python
red1 = Color(255, 0, 0)
red2 = Color(255, 0, 0)
assert red1 == red2  # True - colors are comparable

black = Color(0, 0, 0)
assert black.is_black  # True
```

**Converting colors**:
```python
color = Color(255, 100, 50)

# To RGB tuple (0-255 range)
r, g, b = color.to_rgb()
# r=255, g=100, b=50

# To normalized RGB (0.0-1.0 range)
r_norm, g_norm, b_norm = color.to_rgb_normalized()
# r_norm=1.0, g_norm=0.39, b_norm=0.20

# To hexadecimal string
hex_str = color.to_hex()
# hex_str = '#FF6432'

# With brightness adjustment
r, g, b = color.to_rgb_with_brightness(brightness=0.8)
# Returns RGB adjusted by brightness level
```

### Brightness Levels

**Zone brightness**: Independent per-zone brightness adjustment
- Range: 0.0 to 1.0 (0% to 100%)
- Applies to whatever color is rendered in that zone
- Doesn't change the stored color, just how it's displayed

**Color brightness**: Some effects may adjust color brightness
- Created via `color.with_brightness(factor)`
- Used for animation effects (pulsing, fading)
- Creates new Color object without modifying original

**Combined**: When rendering, both zone brightness and color brightness apply:
```python
# Zone brightness: 0.8 (80%)
# Color brightness from animation: 0.5 (50%)
# Final brightness: 0.8 × 0.5 = 0.4 (40% of max)
# Result: Color displayed at 40% intensity
```

### Color Space Conversion

Colors can be represented in different spaces:

**RGB** (Red, Green, Blue):
- 0-255 for each component
- Most common for LED systems
- Direct hardware output

**HSV** (Hue, Saturation, Value):
- Hue: 0-360° (color wheel position)
- Saturation: 0-100% (color intensity)
- Value: 0-100% (brightness)
- Natural for user input (hue rotation, desaturation)

**HSL** (Hue, Saturation, Lightness):
- Similar to HSV but lightness is center-based
- Better for tints/shades

**System Support**:
- Internal: Can work with any space via Color class
- Conversion: Automatic between RGB and HSV/HSL
- Display: Hardware receives RGB bytes

**Example Use**:
```python
# User wants to rotate hue by 30 degrees
original = Color.from_hsv(hue=120, saturation=100, value=100)  # Green
rotated = original.with_hue_adjustment(30)  # Green → Yellow-green

# What happens internally:
# 1. original converted to RGB: (0, 255, 0)
# 2. Hue adjusted: 120° → 150°
# 3. Convert back to RGB: (0, 255, 127)
# 4. Result displayed
```

### Gamma Correction

LEDs don't respond linearly to brightness. A brightness of 50% doesn't look half as bright to humans.

**Gamma correction**: Mathematical adjustment to make perceived brightness linear.

**System approach**:
- Brightness values are linear (what user intends)
- Gamma correction applied at hardware boundary
- Result: User expects 50% brightness = looks 50% bright

**User perspective**: Doesn't need to think about gamma. The system handles it.

---

## Zone Selection and Navigation

### Zone Selection

The system maintains a **selected zone** (current focus for user interaction).

**User can**:
- Rotate through zones (next/previous)
- Edit selected zone's color (in STATIC mode)
- Toggle selected zone's mode
- Run animation on selected zone

**Behavior**:
```
Selected zone: FLOOR
User rotates forward → Selected zone: LEFT

User edits color → FLOOR color changes
User rotates → Selection moves to LEFT
FLOOR color stays as changed

User starts animation → Animation runs on FLOOR only
Other zones continue their modes
```

### Zone Exclusion in Animations

When an animation starts on the **selected zone**, other zones are **excluded** from that animation.

**Example**:
```
Zones: FLOOR, LEFT, TOP, RIGHT, BOTTOM, LAMP, PIXEL, PIXEL2, PREVIEW
Selected zone: FLOOR

User starts "Rainbow" animation
  ↓
AnimationEngine.start('RAINBOW', excluded_zones=[LEFT, TOP, RIGHT, BOTTOM, LAMP, PIXEL, PIXEL2, PREVIEW])
  ↓
Animation runs on FLOOR only
All other zones display their static colors (or prior animation)
```

**Result**: Rich layered effects are possible:
- FLOOR running animation
- LAMP showing static white light
- Other zones showing static colors
- All simultaneously

---

## Practical Examples

### Example 1: Editing a Zone Color

**Scenario**: User wants to change FLOOR to orange

```
Current state:
├─ FLOOR: STATIC mode, red color
├─ LEFT: ANIMATION mode, breathe effect
└─ Other zones: various

User actions:
1. Select FLOOR zone (if not already selected)
2. Press edit button
3. Adjust hue knob (red → orange)
4. Zone updates: FLOOR now orange, STATIC mode

Result:
├─ FLOOR: STATIC mode, orange color ✓
├─ LEFT: ANIMATION mode, still breathing
└─ Other zones: unchanged
```

### Example 2: Starting an Animation

**Scenario**: User starts a "snake" animation on selected zone (LEFT)

```
Current state:
├─ FLOOR: STATIC mode, blue color
├─ LEFT: STATIC mode, green color
└─ Other zones: static colors

User actions:
1. Select LEFT zone
2. Switch to ANIMATION mode
3. Select "SNAKE" animation
4. Adjust speed parameter

System internal:
- AnimationEngine receives: start(SNAKE, excluded_zones=[FLOOR, others], speed=50)
- SNAKE animation runs generator for LEFT zone only
- Other zones excluded from this animation
- But FLOOR can have its own animation! (independent)

Result:
├─ FLOOR: STATIC mode, blue (unchanged)
├─ LEFT: ANIMATION mode, snake effect ✓
└─ Other zones: unchanged
```

### Example 3: Transition During Animation

**Scenario**: Power off while FLOOR is in animation mode

```
Current state:
├─ FLOOR: ANIMATION mode, rainbow
├─ LEFT: ANIMATION mode, breathe
└─ Other zones: various

User actions:
1. Press power off button

System behavior:
- TransitionService starts FADE_OUT
- Transition generates frames with priority 40 (TRANSITION)
- FrameManager selects transition frames (override animations)
- All LEDs gradually fade to black
- Takes ~500ms for smooth fade
- Animations stop after fade completes
- System enters low-power mode

Result:
└─ All zones: Off (after fade)
```

---

## Zone Configuration

Zones are defined in configuration with:
- **Zone ID**: Unique identifier
- **Display name**: User-friendly name
- **Pixel count**: How many LEDs in this zone
- **Enabled**: Can be toggled on/off
- **Reversed**: Optional pixel reversal
- **Parameters**: Per-zone adjustable settings

**From user perspective**:
- Zones are pre-configured (determined at system setup)
- Can't add zones at runtime (requires reboot)
- Can select/edit/animate them
- Can enable/disable them
- Brightness and color adjustable

**From configuration perspective**:
- Defined in configuration files
- Mapped to physical GPIO pins and pixel indices
- But application never touches those details

---

## Summary

**Zones**:
- Logical groupings of LEDs
- Independent color and mode per zone
- Support STATIC, ANIMATION, and OFF modes
- Can be selected and edited by user
- Enable sophisticated multi-effect experiences

**Colors**:
- First-class domain objects throughout system
- Support multiple color spaces (RGB, HSV, HSL)
- Can be adjusted (brightness, hue)
- Created from presets, values, or conversions
- Only converted to hardware bytes at last moment

**Combined Power**:
- "Set FLOOR to animate with red focus"
- "Keep LEFT static while others animate"
- "Smooth transition between states"
- "Adjust any zone independently"

---

**Next:** [Animations](4_animations.md)
