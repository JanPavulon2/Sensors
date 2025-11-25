---
Last Updated: 2025-11-25
Type: Agent Documentation
Purpose: Overview linking user docs with agent-specific implementation details
---

# Agent Documentation Overview

Welcome, AI agent! This documentation extends the [user documentation](../user/0_overview.md) with implementation-specific details, code locations, and current system state.

## Quick Links

### User Documentation (Start Here)
- [User Overview](../user/0_overview.md) - System concepts and philosophy
- [Architecture Layers](../user/1_architecture_layers.md) - Complete system architecture
- [Hardware Abstraction](../user/2_hardware_abstraction.md) - Hardware independence
- [Zones and Colors](../user/3_zones_and_colors.md) - Zone modes and color handling
- [Animations](../user/4_animations.md) - 9 animation types
- [Frame Priority System](../user/5_frame_priority_system.md) - Priority-based rendering
- [Extending System](../user/6_extending_system.md) - How to add features

### Agent Documentation
1. **[Current Configuration](1_current_configuration.md)** - Actual GPIO, zones, pixels
2. **[Code Map](2_code_map.md)** - File locations and key entry points
3. **[Controller Relationships](3_controller_relationships.md)** - All 9 controllers and dependencies
4. **[Rendering Pipeline Details](4_rendering_pipeline_details.md)** - Code flow with snippets
5. **[Implementation Patterns](5_implementation_patterns.md)** - DI, TYPE_CHECKING, async patterns

## Current System State

**Project**: Diuna LED Control System (Raspberry Pi 4)
**Status**: Phase 6 Complete (Unified Rendering + Type Safety)
**Language**: Python 3.9+ with asyncio
**Hardware**: 2 GPIO pins (GPIO 18, GPIO 19) with 119 total pixels
**Architecture**: 6-layer frame-based priority rendering

## Key Files Reference

| Component | File | Lines |
|-----------|------|-------|
| **Main** | `src/main_asyncio.py` | 364 |
| **FrameManager** | `src/engine/frame_manager.py` | 800+ |
| **AnimationEngine** | `src/animations/engine.py` | 700+ |
| **LEDController** | `src/controllers/led_controller/led_controller.py` | 597 |
| **StaticModeController** | `src/controllers/led_controller/static_mode_controller.py` | 241 |
| **AnimationModeController** | `src/controllers/led_controller/animation_mode_controller.py` | 255 |
| **ZoneStripController** | `src/controllers/zone_strip_controller.py` | 273 |
| **TransitionService** | `src/services/transition_service.py` | 350+ |
| **ZoneStrip** | `src/zone_layer/zone_strip.py` | 250+ |
| **WS281xStrip** | `src/hardware/led/ws281x_strip.py` | 200+ |

**Total rendering system**: ~4,500 lines across 20+ files

## Architecture at a Glance

```
Layer 6: Application (Controllers, EventBus)
  ↓ calls
Layer 5: Services (Transitions, Animations)
  ↓ calls
Layer 4: AnimationEngine (Lifecycle, frame generation)
  ↓ submits frames to
Layer 3: FrameManager (Priority selection, rendering)
  ↓ uses
Layer 2: ZoneStrip (Zone-to-pixel mapping)
  ↓ uses
Layer 1: WS281xStrip (GPIO hardware interface)
```

## Current Configuration

**GPIO 18 (MAIN_12V)**:
- LED Type: WS2811 (12V)
- Color Order: BGR
- Total Pixels: 51
- Zones: FLOOR (15px), LEFT (10px), TOP (10px), RIGHT (10px), BOTTOM (5px), LAMP (1px)

**GPIO 19 (AUX_5V)**:
- LED Type: WS2812B (5V)
- Color Order: GRB
- Total Pixels: 68
- Zones: PIXEL (1px), PIXEL2 (1px), PREVIEW (8px) + 58px spare

## All 9 Controllers

| # | Controller | File | Status | Purpose |
|---|-----------|------|--------|---------|
| 1 | **LEDController** | `led_controller.py` | ✅ ACTIVE | Main orchestrator |
| 2 | **StaticModeController** | `static_mode_controller.py` | ✅ ACTIVE | Zone editing + pulsing |
| 3 | **AnimationModeController** | `animation_mode_controller.py` | ✅ ACTIVE | Animation selection |
| 4 | **ZoneStripController** | `zone_strip_controller.py` | ✅ ACTIVE | Rendering interface |
| 5 | **PowerToggleController** | `power_toggle_controller.py` | ✅ ACTIVE | Power on/off |
| 6 | **LampWhiteModeController** | `lamp_white_mode_controller.py` | ✅ ACTIVE | LAMP white mode |
| 7 | **FramePlaybackController** | `frame_playback_controller.py` | ✅ IMPLEMENTED | Frame-by-frame debugging |
| 8 | **ControlPanelController** | `control_panel_controller.py` | ✅ ACTIVE | Hardware polling |
| 9 | **PreviewPanelController** | `preview_panel_controller.py` | ⚠️ DISABLED | Preview visualization |

**All controllers are in** `src/controllers/led_controller/` **except**:
- ZoneStripController: `src/controllers/zone_strip_controller.py`
- ControlPanelController: `src/controllers/control_panel_controller.py`

## Recent Refactoring (Phase 6)

### Unified Rendering Path
- ✅ All zone rendering through `submit_zone_frame()`
- ✅ All transitions through FrameManager (no direct `show()`)
- ✅ AnimationEngine uses FrameManager for submission
- ✅ Eliminated parallel rendering paths

### Type Safety
- ✅ Fixed Color model circular imports (TYPE_CHECKING pattern)
- ✅ Separated generic frame selection into type-specific methods
- ✅ EventBus with proper TypeVar handling
- ✅ Zero type errors in core rendering path

## Known Issues

**BLOCKING**:
- SnakeAnimation zero division when zone list empty (needs validation in `__init__()`)

**MEDIUM PRIORITY**:
- Ghost pixels: Frames remaining in queue during animation crossfade
- Preview panel not integrated with FrameManager
- Power-off flickering: Animation pixels briefly remain

**LOW PRIORITY**:
- `PixelFrame.clear_other_zones` flag not implemented in FrameManager rendering
- Code repetitions: Color conversion, excluded zones building

## What You Can Do With This Documentation

### Planning Tasks
- Understand system architecture before implementing changes
- Identify which layer your change belongs in
- Check dependencies between components
- Find code to read or modify

### Adding Features
- Adding animations: See Extending System + Implementation Patterns
- New modes: See Controller Relationships + Implementation Patterns
- New hardware: See Hardware Abstraction + Code Map
- Fixing bugs: See Rendering Pipeline Details + Code Map

### Code Review
- Verify architectural adherence (6 layers)
- Check type safety (Color objects, enums, type hints)
- Validate async patterns (await, create_task, etc.)
- Confirm frame submission (no direct `show()` calls)

### Performance Analysis
- Frame manager cycle time: ~16.67ms (60 FPS)
- DMA transfer: ~2.75ms per 90 pixels
- Headroom: ~13.92ms per cycle
- Target: Maintain 60 FPS

## Documentation Structure

### User Documentation (../user/)
**For anyone learning or using the system**:
- Conceptual explanations
- No specific implementation details
- No code locations or file paths
- No zone counts or pixel numbers
- Focused on "how it works" not "what code does it"

### Agent Documentation (/)
**For AI agents working on the code**:
- Implementation details
- Exact file locations and line numbers
- Current system configuration
- Code snippets and patterns
- Specific metrics (zone counts, pixel counts)

## How to Use This Documentation

1. **Start with user docs** (../user/0_overview.md)
   - Understand the system conceptually
   - Learn how layers interact
   - Grasp design principles

2. **Check current configuration** (1_current_configuration.md)
   - See actual zones, GPIO pins, pixel counts
   - Understand GPIO mapping
   - See hardware setup

3. **Reference code map** (2_code_map.md)
   - Find files and entry points
   - Get line numbers for key functions
   - Navigate codebase quickly

4. **Study controller relationships** (3_controller_relationships.md)
   - See all 9 controllers
   - Understand dependencies
   - Check active status

5. **Review pipeline details** (4_rendering_pipeline_details.md)
   - Study code flow with snippets
   - See method signatures
   - Understand data structures

6. **Learn patterns** (5_implementation_patterns.md)
   - DI (dependency injection)
   - TYPE_CHECKING (circular imports)
   - Async patterns
   - Code style conventions

## Important Conventions

### Naming
- ✅ No abbreviations: `hardware`, `config`, `manager`, not `hw`, `cfg`, `mgr`
- ✅ Use enums: `ZoneID.FLOOR`, not `"floor"`
- ✅ Use Color class: `Color(255, 0, 0)`, not `(255, 0, 0)`

### Type Safety
- ✅ All functions have type hints
- ✅ Use isinstance() not hasattr()
- ✅ Circular imports resolved with TYPE_CHECKING

### Async Patterns
- ✅ Always await async calls
- ✅ Use async with for context managers
- ✅ Use asyncio.create_task() for fire-and-forget
- ✅ Cancel tasks in cleanup

### Frame Submission
- ✅ Submit to FrameManager, never call hardware directly
- ✅ Use appropriate frame type (ZoneFrame, PixelFrame, etc.)
- ✅ Always specify priority level
- ✅ Respect TTL (time-to-live)

---

**Next**: [Current Configuration](1_current_configuration.md)

See also: [Project TODO System](../../.todo/rendering_system.md)
