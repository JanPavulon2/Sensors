---
Last Updated: 2025-11-25
Type: User Documentation
Purpose: High-level overview of the rendering system
---

# Rendering System Overview

## What is the Rendering System?

The Diuna LED control system is a sophisticated, event-driven rendering engine designed to drive addressable LED strips with real-time animation and interactive control. The system prioritizes hardware independence, type safety, and clean architectural separation.

## Core Philosophy

### Hardware Independence
The system abstracts away hardware details completely. Internal code works with:
- **Colors** as domain objects (not RGB tuples)
- **Zones** as logical areas (not pixel indices)
- **Animations** as conceptual effects (not hardware commands)

Only at the last possible moment—when sending data to the LED strip—are these converted to raw pixel values.

### Frame-Based Rendering
Instead of directly manipulating LEDs, components submit "frames" to a central frame manager:
1. A component generates a frame (colors for zones or individual pixels)
2. The frame is submitted with a priority level
3. The frame manager selects the highest-priority frame
4. The selected frame is rendered to hardware 60 times per second

This approach provides:
- **Conflict resolution**: When multiple effects want to control the same LED, priority wins
- **Atomic updates**: All LEDs update together, never in partial states
- **Clean interfaces**: Components don't need to coordinate or know about each other

### Color Handling
Colors are first-class domain objects throughout the system:
- Animation code works with `Color` objects
- Colors can be created from various sources (presets, HSV, RGB)
- Colors include metadata (brightness adjustments, etc.)
- Only when sending to hardware are colors converted to RGB byte values

This separation enables:
- Color space flexibility (easily support HSV, HSL, etc.)
- Gamma correction and color temperature management
- Consistent color handling across all modes

## System Architecture

The rendering system consists of **6 layers**, each with specific responsibilities:

| Layer | Purpose | Examples |
|-------|---------|----------|
| **Hardware Layer** | Physical LED communication | GPIO access, DMA transfers, color order mapping |
| **Zone Layer** | Logical zone abstraction | Zone-to-pixel mapping, pixel buffering |
| **Engine Layer** | Centralized rendering | Frame selection by priority, rendering orchestration |
| **Animation System** | Animation lifecycle | Starting/stopping animations, parameter updates |
| **Transition System** | Smooth state changes | Crossfades, fade-in/out effects |
| **Application Layer** | User interaction & coordination | Controllers, event handling, user input routing |

See [1_architecture_layers.md](1_architecture_layers.md) for detailed layer descriptions.

## Key Concepts

### Zones
A **zone** is a logical grouping of LEDs. Instead of manipulating individual pixels, you manipulate zones:
- Each zone has a color, brightness, and enabled/disabled state
- Zones are independent—changing one zone's color doesn't affect others
- Animations can run on specific zones while others remain static

### Animations
An **animation** is an effect that changes colors over time. The system supports:
- **Preset animations** with parameters (speed, intensity, color)
- **Per-zone animations** (animation only affects selected zone)
- **Full-strip animations** (animation affects all pixels)
- **Generator-based** (animations are Python async generators)

### Frames & Priority
A **frame** represents the complete or partial LED state at one moment:
- Frames have a **priority level** (0-100, higher wins)
- Frames have a **TTL** (time-to-live before expiring)
- Each render cycle, the highest-priority non-expired frame is displayed

**Priority levels**:
- `0` (IDLE): Default, empty state
- `10` (MANUAL): Static manual colors
- `20` (PULSE): Edit mode pulsing effect
- `30` (ANIMATION): Normal animations
- `40` (TRANSITION): Smooth state transitions
- `50` (DEBUG): Debugging/testing frames

### Modes
Each zone can be in different **modes**:
- **STATIC**: Shows a fixed color, user can edit
- **ANIMATION**: Running an animation, parameters adjustable
- **OFF**: Zone disabled

Zones are independent—one can be static while another runs an animation.

## System Flow

```
User Input (keyboard, buttons, knobs)
    ↓
Controllers (interpret input, decide action)
    ↓
Services (animate, transition, update state)
    ↓
Frame Submission (components submit frames with priority)
    ↓
Frame Manager (selects highest priority, renders)
    ↓
Hardware (sends data to LED strips via GPIO)
```

## Getting Started

- **New to the system?** Read [1_architecture_layers.md](1_architecture_layers.md)
- **Want to understand colors?** See [2_hardware_abstraction.md](2_hardware_abstraction.md) and [3_zones_and_colors.md](3_zones_and_colors.md)
- **Interested in animations?** Read [4_animations.md](4_animations.md)
- **Need to extend the system?** See [6_extending_system.md](6_extending_system.md)

---

**Next:** [Architecture Layers](1_architecture_layers.md)