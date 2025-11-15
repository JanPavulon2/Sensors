---
Last Updated: 2025-11-15
Created By: Migration from root CLAUDE.md
Purpose: System architecture overview
---

# System Architecture Overview

## Critical Instructions
- ALL instructions MUST BE FOLLOWED unless explicitly optional
- ASK FOR CLARIFICATION if uncertain
- DO NOT edit more code than necessary
- DO NOT WASTE TOKENS - be succinct and concise

## System Summary
Raspberry Pi LED controller with 90 addressable WS2811 LEDs across 8 zones.
- **Architecture**: 5-layer asyncio-based event-driven system
- **Modes**: STATIC (zone editing) ↔ ANIMATION (animation control)
- **Input**: 2 rotary encoders, 4 buttons, keyboard support
- **Preview**: 8-LED panel for parameter visualization

## 5-Layer Architecture
```
Layer 4: Infrastructure → ConfigManager, EventBus, DataAssembler, Logging
Layer 3: Application    → LEDController, Feature Controllers
Layer 2: Domain         → Services (Zone/Animation), Domain Models
Layer 1: HAL            → Components (ZoneStrip, ControlPanel, PreviewPanel)
Layer 0: GPIO           → GPIOManager (pin registry, conflict detection)
         ↓
    Hardware Drivers    → RPi.GPIO, rpi_ws281x
```

## Key Components

**LEDController** (`src/controllers/led_controller/led_controller.py`)
- Main state machine, orchestrates everything
- Delegates to feature controllers: Static/Animation/LampWhite/PowerToggle

**AnimationEngine** (`src/animations/engine.py`)
- Manages animation lifecycle, consumes async frame generators
- Submits frames to FrameManager with priority

**FrameManager** (`src/engine/frame_manager.py`)
- Priority-based frame selection (TRANSITION > ANIMATION > PULSE > MANUAL)
- Atomic rendering: single `show()` per 60Hz tick
- Prevents flickering and race conditions

**EventBus** (`src/services/event_bus.py`)
- Pub-sub pattern decouples hardware from logic
- Priority handlers, middleware, fault isolation

## Data Flow Example
```
Encoder Rotate → GPIO Change → ControlPanel.poll() 
  → Publish Event → EventBus → LEDController handler
  → Service method → Update domain → DataAssembler.save()
  → state.json written
```

## State Management
- **Auto-save**: Every user action saves to `state/state.json`
- **No periodic saves**: Event-driven only
- **Repository Pattern**: Only DataAssembler touches state.json

## Configuration
- **Modular YAML**: `config.yaml` includes hardware/zones/colors/animations/parameters.yaml
- **Single Loader**: ConfigManager is ONLY component that loads files
- **Dependency Injection**: Sub-managers receive processed data

## Design Patterns
1. **Event-Driven**: EventBus decouples components
2. **DDD**: Config (immutable) + State (mutable) + Combined (aggregate)
3. **Repository**: DataAssembler handles all persistence
4. **Service**: ZoneService/AnimationService coordinate operations
5. **Async Generators**: Animations yield frames

## Hardware Constraints
- **WS2811 Timing**: 2.7ms DMA + 50µs reset = 2.75ms min/frame
- **Target FPS**: 60Hz (leaves 40% headroom)
- **GPIO Limits**: Only pins 10,12,18,21 support WS281x
- **Pi Model**: Pi 4 recommended (20-30% CPU @ 60fps)

## File Locations
- Entry: `src/main_asyncio.py`
- Main controller: `src/controllers/led_controller/led_controller.py`
- Animations: `src/animations/*.py`
- Services: `src/services/*.py`
- Config: `src/config/*.yaml`