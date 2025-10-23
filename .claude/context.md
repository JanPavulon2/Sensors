# Diuna Project Context

## Project Overview
Raspberry Pi LED control station with zone-based addressable RGB LED control, rotary encoder UI, and animation system. Runs asyncio event loop for non-blocking hardware polling.

**Hardware**: WS2811 (12V) addressable LEDs controlled via rpi_ws281x library. Two separate strips (preview panel + main strip), 2 rotary encoders, 4 buttons.

## Project Scope

**Primary codebase**: `src/` directory only

**Directory structure**:
```
src/
├── animations/       # Animation implementations (breathe, snake, color_fade, etc.)
├── components/       # Hardware components (ZoneStrip, PreviewPanel)
├── config/           # YAML configuration files (modular structure)
├── managers/         # Sub-managers (HardwareManager, ZoneManager, AnimationManager, etc.)
├── models/           # Data models (Color, Parameter, Zone) and enums
├── utils/            # Utility functions (colors, logger)
└── tests/            # Test files
```

**Excluded from context**:
- `/backups/` - old backups
- `/old_working/` - deprecated code
- `/samples/` - example files only
- `/diunaenv/` - virtual environment
- Root-level config files

## Architecture Principles

1. **Modular YAML Configuration**
   - `config.yaml` - include-based main config
   - `hardware.yaml` - GPIO pins, encoders, buttons, LED strips
   - `zones.yaml` - Zone definitions and parameters
   - `animations.yaml` - Animation definitions and parameters
   - `colors.yaml` - Color preset definitions
   - `factory_defaults.yaml` - Factory reset fallback

2. **Manager Pattern**
   - `ConfigManager` - Loads config via include system, initializes sub-managers
   - `HardwareManager` - Hardware configuration access
   - `ZoneManager` - Zone collection, auto-calculates indices
   - `AnimationManager` - Animation metadata and registration
   - `ColorManager` - Color preset management
   - `StateManager` - Async JSON state persistence

3. **AppContext Pattern**
   - Single access point for config + state
   - Glues ConfigManager and StateManager
   - Injected into LEDController

4. **Event-Driven State Machine**
   - Asyncio-based with central LEDController
   - Hardware events → ControlModule callbacks → LEDController
   - Non-blocking animations and pulsing

5. **Single Source of Truth**
   - Zone colors: `zone_hues` dict (0-360 hue values)
   - Config: YAML files (read-only)
   - State: JSON file (dynamic, auto-saved)

## Development Focus

All development work focuses on the `src/` directory structure. See [CLAUDE.md](../CLAUDE.md) for detailed technical documentation.
