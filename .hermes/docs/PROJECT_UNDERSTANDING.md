# Aurora System - Current Understanding

## Executive Summary
Aurora (formerly Diuna) is a sophisticated LED control system running on Raspberry Pi that provides real-time LED frame rendering with zone-based control, animations, and a web frontend interface. The system is designed for extensibility and is now evolving toward a multi-device architecture.

## Core Architecture (Single-Host Current State)

### Application Entry Point
- **File**: `src/main_asyncio.py`
- **Startup Sequence**:
  1. Infrastructure Setup (GPIO manager, YAML config loading, EventBus, state loading)
  2. Service Initialization (AnimationService, ApplicationStateService, ZoneService, ServiceContainer)
  3. Hardware Stack (HardwareCoordinator, LedChannel instances, zone registration with FrameManager)
  4. FrameManager Startup (60 FPS render loop, LED channel registration, TransitionService)
  5. Controllers (LightingController - main orchestrator, ControlPanelController - hardware input)
  6. API Server (FastAPI + Socket.IO app on 0.0.0.0:8000)
  7. Graceful Shutdown (ShutdownCoordinator, signal handlers)

### Key Systems

#### 1. Frame Rendering System
- **FrameManager**: Manages priority queues with intelligent merging
- **Render Loop**: 60 FPS (_render_loop → _drain_frames)
- **Frame Priorities** (highest to lowest):
  - DEBUG (50) - Future overlays
  - TRANSITION (40) - Crossfades, mode switches
  - PULSE (30) - Edit mode effects
  - ANIMATION (20) - Base animations
  - MANUAL (10) - Static zone editing
  - IDLE (0) - Black fallback

#### 2. Zone System
- **ZoneConfig** (immutable, from YAML): id, display_name, start_pixel, end_pixel, led_channel, render_mode
- **ZoneState** (mutable): is_on, color_mode, color_preset, brightness, color_hue, color_value, render_mode, transitioning
- **Zone Types**:
  - SingleZoneFrame: one zone → one color
  - MultiZoneFrame: many zones → one color each  
  - PixelFrame: many zones → List[Color] each (pixel-level)
  - CompositeFrame/OutputFrame: Internal unified representation / Final streaming snapshot

#### 3. Animation System
- **BaseAnimation**: Abstract base class with step() method
- **AnimationEngine**: Manages animation tasks per zone
- **Built-in Animations**:
  - Breathe: Sinusoidal brightness modulation
  - Snake: Moving single-color segment
  - ColorSnake: Rainbow snake with hue drift
  - ColorFade: Smooth color transitions
- **Animation Parameters**: SPEED, BRIGHTNESS, HUE, COLOR, INTENSITY, PRIMARY_COLOR_HUE, LENGTH

#### 4. Color System
- **Color Class**: RGB with methods for brightness adjustment, hue manipulation, preset conversion
- **ColorManager**: Manages preset colors from colors.yaml
- **Preset Categories**: basic, white, warm, cool, natural, special
- **Cycling Order**: 20 presets in specific sequence for modulation

#### 5. Event System
- **EventBus**: Publish-subscribe with middleware support
- **Event Types**:
  - Hardware: ENCODER_ROTATE, ENCODER_CLICK, BUTTON_PRESS, KEYBOARD_KEYPRESS
  - Zone: ZONE_STATIC_STATE_CHANGED, ZONE_RENDER_MODE_CHANGED, ZONE_ANIMATION_CHANGED, ZONE_SNAPSHOT_UPDATED
  - Animation: ANIMATION_STARTED, ANIMATION_STOPPED, ANIMATION_PARAMETER_CHANGED
- **Features**: Middleware pipeline, event history, priority-based handler execution, fault isolation

#### 6. API & Real-Time
- **FastAPI Backend**: REST API for system control, zone config, animation control
- **Socket.IO**: Real-time frame streaming to frontend
- **FrameStreamer**: Handles frame serialization and emission
- **Frontend**: Visual interface for zone control, animation selection, parameter adjustment, frame monitoring

#### 7. Hardware Abstraction
- **GPIO Manager**: Singleton for GPIO pin management
- **HardwareCoordinator**: Initializes LED strips, creates LedChannel instances
- **LedChannel**: Abstracts WS2811/WS2812 strips on specific GPIO pins
- **Current Setup**: 
  - GPIO 18: WS2811 12V strip
  - GPIO 19: WS2812 5V strip
- **Zone Mapping**: Zones map to specific pixel ranges on LED channels

#### 8. State Management
- **ApplicationStateService**: Manages global application state
- **Persistence**: state.json stores zone configuration, animation parameters, system modes
- **Loading**: State loaded during startup

## Current Limitations
1. **Single-Host Architecture**: All rendering happens on Raspberry Pi
2. **Limited Scalability**: Adding more LED strips increases host load
3. **Centralized Processing**: No distribution of computational load
4. **Static Zone Mapping**: Zones defined by start/end pixel indices only

## Planned Enhancements (Multi-Device Vision)

### 1. Host/Node Architecture
- **Host (Raspberry Pi 5)**: System management, configuration, API, real-time frontend, coordination
- **Nodes**: 
  - ESP32: Remote rendering nodes for local LED strips
  - Raspberry Pi 4: Additional rendering capacity
- **Responsibilities**:
  - Host: Orchestration, user interface, configuration distribution, time synchronization
  - Nodes: Local frame rendering based on received instructions, direct hardware control

### 2. Communication Strategy
- **WebAPI**: Existing backend→frontend communication (likely to be reused for host↔node config/control)
- **Real-time Transport**: Need to evaluate options (MQTT, WebSocket, custom UDP) for frame data
- **Synchronization**: Central clock (AppCoy) with frame buffering and periodic re-sync
- **Configuration**: Initial load at startup + dynamic updates

### 3. Enhanced LED Mapping
- **Current**: Linear mapping ("LED #5 in strip sequence")
- **Planned**: 2D/3D shape-based mapping 
- **Example**: "Pixels 6-26 form a 3×4 rectangle panel"
- **Benefits**: More intuitive spatial animations, better mapping to physical layouts

### 4. Distributed Rendering
- **Frame Computation**: Nodes calculate animation frames locally based on zone definitions and parameters
- **Data Efficiency**: Host sends lightweight instructions (animation type, parameters, timestamps) vs. full pixel data
- **Fault Tolerance**: Nodes can continue last known good state if host connection drops temporarily

## Technical Stack Confirmation
- **Language**: Python 3.8+
- **Async Framework**: asyncio
- **Backend**: FastAPI
- **Real-time**: Socket.IO (currently frontend, potentially extensible)
- **Frontend**: React + Tailwind CSS
- **Configuration**: YAML files
- **Testing**: pytest
- **Hardware**: GPIO with WS2811/WS2812 LED strip support

## Immediate Next Steps for Multi-Device Transition
1. Define clear host/node responsibility boundaries
2. Design communication protocol(s) between host and nodes
3. Adapt zone configuration for distribution to nodes
4. Modify FrameManager to work in distributed mode
5. Create node firmware/software for ESP32 and Raspberry Pi nodes
6. Implement synchronization mechanism
7. Test with mixed host/node setup