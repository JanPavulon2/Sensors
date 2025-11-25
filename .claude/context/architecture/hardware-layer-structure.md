---
Last Updated: 2025-11-18
Updated By: @architecture-expert-sonnet
Changes: Complete hardware layer architecture analysis and refactoring recommendations
---

# Hardware Layer Structure Analysis & Recommendations

## Current State

Your codebase has **excellent separation of concerns** across three distinct layers. Currently, however, the **initialization orchestration** (Strip creation, configuration, wiring) is scattered in `main_asyncio.py` lines 188-254.

## 🏗️ Three-Layer Architecture (Current + Proposed)

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: APPLICATION (Stateless, User-Facing)                   │
│ ──────────────────────────────────────────────────────────────  │
│  - LEDController (main orchestrator)                            │
│  - Mode controllers (animation, static, power, etc.)            │
│  - Domain services (ZoneService, AnimationService, etc.)        │
│  - Event handling & state management                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (uses)
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: CONTROL (Request Processing & Coordination)            │
│ ──────────────────────────────────────────────────────────────  │
│  - ZoneStripController (delegates rendering to FrameManager)    │
│  - PreviewPanelController (preview display logic)               │
│  - ControlPanelController (input polling → events)              │
│  - TransitionService (fade effects, frame transitions)          │
│  - FrameManager (async frame render loop)                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (uses)
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: HARDWARE (Stateless, Direct Hardware Access)          │
│ ────────────────────────────────────────────────────────────── │
│  Components (Low-level device abstractions):                    │
│    - ZoneStrip (WS281x strip with zone mapping)                │
│    - PreviewPanel (CJMCU-2812-8 8-pixel module)                │
│    - RotaryEncoder, Button, ControlPanel (input devices)       │
│  Infrastructure:                                                │
│    - GPIOManager (pin registration & cleanup)                  │
│    - LEDHardware (raw PixelStrip initialization) [*]           │
│    - HardwareManager (config provider)                         │
│  [*] LEDHardware creates raw PixelStrips but is NOT USED       │
└─────────────────────────────────────────────────────────────────┘
```

## 🔴 Current Issues

### Issue #1: LEDHardware is Dead Code
**Location**: `src/hardware/led/led_hardware.py` (imported but never used)

**Problem**:
- Initializes raw `PixelStrip` objects for MAIN_12V (GPIO18) and AUX_5V (GPIO19)
- **But** `main_asyncio.py` ignores this and creates its own ZoneStrips with embedded PixelStrips
- Violates DRY principle — same config in two places
- Causes confusion about which strip is "canonical"

**Root Cause**:
- LEDHardware was designed for single-strip systems
- Your system evolved to **multi-GPIO architecture** with zone-per-GPIO mapping
- LEDHardware wasn't updated accordingly

### Issue #2: Strip Initialization Logic in main_asyncio
**Location**: `src/main_asyncio.py:188-254` (56 lines)

**Problem**:
- Hardcoded GPIO config, DMA/PWM mappings, zone grouping
- Complex logic: grouping zones by GPIO, calculating pixel counts, creating ZoneStrips
- Belongs in Layer 1 (infrastructure), not main entry point
- Makes testing main loop logic difficult

### Issue #3: No Factory/Builder Pattern
**Problem**:
- Creating ZoneStrips requires:
  1. Knowing GPIO pin, DMA, PWM, color order
  2. Grouping zones by GPIO
  3. Calculating per-GPIO pixel counts
  4. Creating PixelStrips with correct parameters
  5. Initializing ZoneStrip wrapper
- This is **infrastructure setup**, not orchestration
- No reusable pattern if you add more strips in future

## ✅ Proposed Solution

### Refactoring Plan

#### Phase 1: Consolidate Hardware Config
**Goal**: Single source of truth for GPIO pinout

**Option A: Extend HardwareManager** (Recommended)
```python
# src/managers/hardware_manager.py (add methods)

class HardwareManager:
    # Existing: get_encoder(), button_pins, etc.

    # NEW - GPIO pinout registry
    def get_gpio_config(self) -> Dict[int, GPIOConfig]:
        """Return {gpio_pin: GPIOConfig(...)}"""
        return {
            18: GPIOConfig(dma=10, pwm=0, color_order=ws.WS2811_STRIP_GRB),
            19: GPIOConfig(dma=11, pwm=1, color_order=ws.WS2812),
        }

    def get_zones_for_gpio(self, gpio: int) -> List[ZoneConfig]:
        """Return zones assigned to this GPIO"""
        # Queries internal zone registry
```

**Why**: Keeps all hardware config in one place, alongside encoders/buttons.

---

#### Phase 2: Create StripFactory
**Goal**: Encapsulate "create ZoneStrip from zones and GPIO" logic

**Location**: `src/hardware/strip_factory.py`

```python
from typing import Dict, List
from rpi_ws281x import ws
from components import ZoneStrip
from models.domain import ZoneConfig
from infrastructure import GPIOManager
from managers.hardware_manager import HardwareManager
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.HARDWARE)

class StripFactory:
    """
    Factory for creating ZoneStrip instances from zone configs and GPIO assignments.

    Responsibilities:
    - Group zones by GPIO
    - Query GPIO config (DMA, PWM, color order)
    - Create PixelStrips with correct hardware parameters
    - Wrap in ZoneStrip with zone mappings
    - Log initialization details
    """

    def __init__(self, hardware_manager: HardwareManager, gpio_manager: GPIOManager):
        self.hardware_manager = hardware_manager
        self.gpio_manager = gpio_manager

    def create_zone_strips(self, zones: List[ZoneConfig]) -> Dict[int, ZoneStrip]:
        """
        Create ZoneStrip for each GPIO based on zone assignments.

        Args:
            zones: All zones from zone_service.get_all()

        Returns:
            Dict[gpio_pin: ZoneStrip]

        Process:
        1. Group zones by GPIO
        2. For each GPIO:
           a. Query GPIO config (DMA, PWM, color order)
           b. Calculate total pixel count
           c. Create ZoneStrip with zones
        3. Return dict for main_asyncio to use with FrameManager
        """
        # Group zones by GPIO
        zones_by_gpio = self._group_zones_by_gpio(zones)

        # Get GPIO config
        gpio_configs = self.hardware_manager.get_gpio_config()

        # Create strips
        zone_strips = {}
        for gpio_pin in sorted(zones_by_gpio.keys()):
            zones_for_gpio = zones_by_gpio[gpio_pin]
            gpio_config = gpio_configs.get(gpio_pin)

            if not gpio_config:
                log.warning(f"No GPIO config for pin {gpio_pin}, skipping")
                continue

            # Calculate pixel count
            pixel_count = sum(z.pixel_count for z in zones_for_gpio)

            # Create ZoneStrip
            strip = ZoneStrip(
                gpio=gpio_pin,
                pixel_count=pixel_count,
                zones=zones_for_gpio,
                gpio_manager=self.gpio_manager,
                dma_channel=gpio_config.dma,
                pwm_channel=gpio_config.pwm,
                color_order=gpio_config.color_order,
                brightness=255
            )

            zone_strips[gpio_pin] = strip
            log.info(f"Created ZoneStrip on GPIO {gpio_pin} "
                    f"(DMA {gpio_config.dma}, PWM {gpio_config.pwm}) "
                    f"with {pixel_count} pixels ({len(zones_for_gpio)} zones)")

        return zone_strips

    def _group_zones_by_gpio(self, zones: List[ZoneConfig]) -> Dict[int, List[ZoneConfig]]:
        """Group zone configs by their assigned GPIO pin."""
        groups = {}
        for zone in zones:
            gpio = zone.gpio
            if gpio not in groups:
                groups[gpio] = []
            groups[gpio].append(zone)
        return groups
```

**Inject into main_asyncio**:
```python
# In main():
from hardware.strip_factory import StripFactory

strip_factory = StripFactory(config_manager.hardware_manager, gpio_manager)
zone_strips = strip_factory.create_zone_strips(zone_service.get_all())
```

---

#### Phase 3: Delete Dead Code
**Cleanup**:
- ❌ Remove `src/hardware/led/led_hardware.py` (unused)
- Remove import from `main_asyncio.py:44`
- Update `src/hardware/led/__init__.py` if needed

---

### New Folder Structure

```
src/
├── hardware/
│   ├── gpio/
│   │   ├── gpio_manager.py       # (unchanged)
│   │   └── __init__.py
│   ├── led/
│   │   ├── __init__.py           # (empty or minimal)
│   │   └── [led_hardware.py]     # ❌ DELETE
│   ├── strip_factory.py           # ✅ NEW
│   └── __init__.py
├── components/
│   ├── zone_strip.py              # (unchanged - owns PixelStrip creation)
│   ├── preview_panel.py           # (unchanged)
│   ├── control_panel.py           # (unchanged)
│   └── __init__.py
├── infrastructure/
│   ├── gpio_manager.py            # (unchanged)
│   └── __init__.py
├── managers/
│   ├── hardware_manager.py        # (extend with GPIO config)
│   ├── config_manager.py          # (unchanged)
│   └── __init__.py
├── controllers/
│   ├── zone_strip_controller.py   # (unchanged)
│   ├── preview_panel_controller.py # (unchanged)
│   └── __init__.py
├── engine/
│   └── frame_manager.py            # (unchanged)
├── services/
│   ├── transition_service.py       # (unchanged)
│   ├── zone_service.py             # (unchanged)
│   └── __init__.py
├── main_asyncio.py                 # ✅ SIMPLIFIED (188-254 → 15 lines)
└── ...
```

---

## 📊 Before & After

### Before (Current)
```python
# main_asyncio.py:188-254 (56 lines of infrastructure logic)
zone_strips = {}
all_zones = zone_service.get_all()

# Group zones by GPIO
zones_by_gpio = {}
for zone in all_zones:
    gpio = zone.config.gpio
    if gpio not in zones_by_gpio:
        zones_by_gpio[gpio] = []
    zones_by_gpio[gpio].append(zone.config)

# Map GPIO pins to DMA channels
gpio_to_dma = {18: 10, 19: 11}
gpio_to_pwm = {18: 0, 19: 1}
gpio_to_color_schema = {
    18: ws.WS2811_STRIP_GRB,
    19: ws.WS2812
}

# Create a ZoneStrip for each GPIO
for gpio_pin, zones_for_gpio in sorted(zones_by_gpio.items()):
    pixel_count_for_gpio = sum(z.pixel_count for z in zones_for_gpio)
    dma_channel = gpio_to_dma.get(gpio_pin, 10)
    pwm_channel = gpio_to_pwm.get(gpio_pin, 0)
    color_order = gpio_to_color_schema.get(gpio_pin, ws.WS2811_STRIP_GRB)

    strip = ZoneStrip(...)
    zone_strips[gpio_pin] = strip
    log.info(...)

zone_strip = zone_strips.get(18, list(zone_strips.values())[0])
# ... (more logic)
```

### After (Proposed)
```python
# main_asyncio.py:188-194
log.info("Initializing LED strips...")
from hardware.strip_factory import StripFactory

strip_factory = StripFactory(config_manager.hardware_manager, gpio_manager)
zone_strips = strip_factory.create_zone_strips(zone_service.get_all())

# Use primary strip (GPIO 18) for controllers
zone_strip = zone_strips.get(18, list(zone_strips.values())[0])
```

**Reduction**: 56 lines → 10 lines (-82%)

---

## 🎯 Benefits of This Refactoring

### Separation of Concerns
- ✅ `main_asyncio.py` stays **orchestration-focused** (DI, startup, shutdown)
- ✅ `StripFactory` owns **infrastructure setup logic** (Layer 1)
- ✅ `HardwareManager` is **single source of truth** for hardware config

### Testability
- ✅ Can test `StripFactory` independently with mock `HardwareManager`
- ✅ Can test `main()` without hardware initialization details
- ✅ Can mock zone_service and get predictable strip creation

### Extensibility
- ✅ Adding third GPIO? Just update `HardwareManager.get_gpio_config()`
- ✅ Adding more zones? No changes to `main_asyncio.py`
- ✅ Changing DMA/PWM mapping? Update config, factory handles it

### Clarity
- ✅ "How do I create zones strips?" → Look at `StripFactory`
- ✅ "Where is GPIO config?" → Look at `HardwareManager`
- ✅ "What is main_asyncio doing?" → Orchestration, not details

### Maintainability
- ✅ Config centralized (not scattered in main_asyncio)
- ✅ Logic reusable (not hidden in entry point)
- ✅ Code symmetry: similar to how you handle buttons/encoders

---

## 🚀 Implementation Priority

| Phase | Effort | Impact | Do First? |
|-------|--------|--------|-----------|
| 1. Extend HardwareManager | Low | High | ✅ Yes |
| 2. Create StripFactory | Medium | High | ✅ Yes |
| 3. Refactor main_asyncio | Low | High | ✅ Yes |
| 4. Delete LEDHardware | Trivial | Medium | ✅ Yes |

**Total refactoring time**: ~30-45 min if done step-by-step

---

## 🔗 Related Files (No Changes Needed)

These remain unchanged:
- `src/components/zone_strip.py` — Keeps PixelStrip creation logic (correct location)
- `src/components/preview_panel.py` — No changes needed
- `src/controllers/*` — No changes needed
- `src/engine/frame_manager.py` — No changes needed
- `src/services/*` — No changes needed

---

## Summary

Your hardware architecture is **already well-designed**. This refactoring simply:
1. **Deletes dead code** (LEDHardware)
2. **Extracts initialization logic** into Layer 1 (StripFactory)
3. **Centralizes config** in HardwareManager
4. **Simplifies main_asyncio** (primary entry point)

No functionality changes — purely structural cleanup for maintainability and extensibility.

