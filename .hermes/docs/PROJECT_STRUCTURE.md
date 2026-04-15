# Aurora System - Project Structure

## Overview
This document outlines the current structure of the Aurora system based on examination of the codebase.

## Root Directory
```
/mnt/c/Repositories/Aurora_System/Sensors/
```

## Main Source Directory: src/
```
src/
├── animations/          # Animation definitions and engine
│   ├── base.py         # Base animation class
│   ├── breathe.py      # Breathe animation
│   ├── color_fade.py   # Color fade animation
│   ├── color_snake.py  # Color snake animation
│   ├── engine.py       # Animation engine
│   ├── rainbow.py      # Rainbow animation
│   ├── snake.py        # Snake animation
│   └── __init__.py
│
├── api/                 # FastAPI backend
│   ├── dependencies.py # Dependency injection
│   ├── dto/            # Data Transfer Objects
│   │   ├── zone_snapshot_dto.py
│   │   └── __init__.py
│   ├── main.py         # FastAPI app entry point
│   ├── middleware/     # Custom middleware
│   │   ├── auth.py
│   │   ├── error_handler.py
│   │   ├── websocket_validation.py
│   │   └── __init__.py
│   ├── models/         # Pydantic models
│   │   └── __init__.py
│   ├── routes/         # API endpoints
│   │   ├── animations.py
│   │   ├── frames.py
│   │   ├── logger.py
│   │   └── ...
│   └── ...
│
├── backend/             # Backend services
├── config/              # Configuration files
├── controllers/         # Hardware and logic controllers
├── engine/              # Core rendering engine
├── hardware/            # Hardware abstraction layer
├── lifecycle/           # Application lifecycle management
├── managers/            # Manager classes for various systems
├── models/              # Data models
├── obsolete/            # Deprecated code
├── runtime/             # Runtime utilities
├── services/            # Service implementations
├── state/               # State management
├── utils/               # Utility functions
├── zone_layer/          # Zone-based rendering system
└── main_asyncio.py      # Application entry point
```

## Key Components Identified

### 1. Animation System
- Located in `src/animations/`
- Uses base class pattern with specific animation implementations
- Managed by AnimationEngine

### 2. API Layer
- FastAPI-based REST API in `src/api/`
- Real-time communication via Socket.IO
- DTOs for data transfer
- Middleware for authentication, error handling, validation

### 3. Hardware Abstraction
- LED channels abstraction (WS2811/WS2812 support)
- Zone-based mapping system
- Input handling (buttons, encoders, keyboard)

### 4. Frame Rendering System
- FrameManager with priority queues
- CompositeFrame/OutputFrame architecture
- 60 FPS render loop
- Zone system with YAML configuration

### 5. Lifecycle Management
- Shutdown coordination
- Task registry and cancellation handling
- Graceful startup/shutdown procedures

## Current Limitations (from now.md)
- Single-host architecture (rendering centralized on Raspberry Pi)
- Zone definitions in YAML files
- Limited to local LED strips

## Planned Enhancements
1. Multi-device architecture (Host/Node separation)
2. 2D LED mapping (shape-based mapping)
3. ESP32 as remote rendering nodes
4. Distributed frame computation

## Documentation Location
Documentation should be maintained in:
- `/mnt/c/Repositories/Synteza_Group/vault/Sekcje/Aurora Systems/`
- Or locally in `/mnt/c/Repositories/Aurora_System/Sensors/docs/` for code-adjacent docs

## Next Steps for Orchestrator Agent
1. Create skill for project orchestration
2. Establish documentation standards
3. Create task management system
4. Set up code review and quality gates