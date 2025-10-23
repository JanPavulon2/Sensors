# Diuna - Raspberry Pi LED Control Station

## Project Status
**Status**: Active development - Config system refactoring in progress

## Hardware Specification

### Raspberry Pi
- **Model**: Raspberry Pi 4
- **OS**: Raspberry Pi OS (Linux 6.12.47+rpt-rpi-v8)

### LED Hardware
- **Main Strip**: WS2811 12V (45 pixels = 15 ICs × 3 LEDs, color order: BRG)
  - GPIO: 18 (PWM0)
  - Zones: strip, lamp, top, right, bottom, left
  - Total: 135 physical LEDs (45 × 3)
- **Preview Panel**: CJMCU-2812-8 (8 pixels, color order: GRB)
  - GPIO: 19 (PCM/PWM1)

### Input Hardware
- **Encoders**: 2x rotary encoders (zone selector + modulator)
  - Zone selector: CLK=5, DT=6, SW=13
  - Modulator: CLK=16, DT=20, SW=21
- **Buttons**: 4x momentary buttons [GPIO 22, 26, 23, 24]
  - BTN1 (22): Toggle edit mode
  - BTN2 (26): Quick lamp white mode
  - BTN3 (23): Power toggle
  - BTN4 (24): Reserved

### Power Supply
- **LED Power**: 12V (WS2811 requirement)
- **Logic Level**: 3.3V (Raspberry Pi GPIO)
- **Level Shifter**: Not used (GPIO 18/19 work directly - may be library-specific)

## Software Stack

### Core Technologies
- **Language**: Python 3
- **Async Framework**: asyncio (non-blocking event loop)
- **LED Library**: rpi_ws281x (requires sudo for PWM DMA access)
- **Config Format**: YAML (modular include-based)
- **State Persistence**: JSON (async aiofiles)

### Key Features
- ✅ Zone-based LED control (6 zones)
- ✅ Dual color modes (HUE 0-360° / PRESET cycling)
- ✅ Edit mode with pulsing indicator
- ✅ Lamp white mode (warm white override)
- ✅ Power toggle with state restore
- ✅ Animation system (breathe, color_fade, snake, color_snake)
- ✅ Parameter system (type-safe, validation)
- ✅ State persistence (auto-save on user action)
- 🚧 **IN PROGRESS**: Modular config refactoring (include-based YAML)

## Current Development Phase

### Config System Refactoring
**Goal**: Split monolithic config.yaml into modular files with manager pattern

**Structure**:
```
config/
├── config.yaml           # Include-based main config
├── hardware.yaml         # GPIO, encoders, buttons, LED strips
├── zones.yaml            # Zone definitions + parameters
├── animations.yaml       # Animation definitions + parameters
├── colors.yaml           # Color presets
└── factory_defaults.yaml # Factory reset fallback
```

**Managers**:
- ConfigManager - Include system, initializes sub-managers
- HardwareManager - Hardware config access
- ZoneManager - Zone collection, auto-index calculation ✅
- AnimationManager - Animation metadata ✅
- ColorManager - Color preset management ✅
- StateManager - Async JSON persistence ✅

**Integration**:
- AppContext - Glue layer for config + state (in progress)
- LEDController - Refactor to use AppContext (pending)

## Known Issues & Constraints

### Hardware Limitations
- **GPIO 19 WS281x support**: Works in current setup but not officially supported (GPIOs 10, 12, 18, 21 are documented)
- **No hot-swap**: Encoders/buttons require reboot if reconnected
- **PWM DMA requirement**: Must run with sudo for rpi_ws281x

### Software Constraints
- **Hue-only rendering**: RGB→HUE conversion loses saturation (white presets render as saturated colors)
- **Fixed pulse speed**: 1.0s cycle (independent from animation_speed by design)
- **No migration system**: State file schema changes require manual adjustment or factory reset

## Running the Application

```bash
# Activate virtual environment
source diunaenv/bin/activate

# Run (requires sudo for GPIO/WS281x)
sudo diunaenv/bin/python3 src/main_asyncio.py

# Exit: Ctrl+C (gracefully saves state)
```

## Documentation
See [CLAUDE.md](../CLAUDE.md) for detailed technical documentation and architecture guide.
