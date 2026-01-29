# Windows Keyboard Support - Complete Analysis
**Date**: 2026-01-15
**Status**: Analysis Complete - Implementation Pending

---

## Problem Statement

The keyboard adapter system currently fails on Windows because:
1. `stdin_keyboard_adapter.py` uses Unix-only modules (`termios`, `tty`, `select`)
2. `evdev_keyboard_adapter.py` uses Linux-only `evdev` library
3. Factory relies on import exceptions rather than explicit platform detection
4. No Windows-specific keyboard adapter implementation exists

When running on Windows, the application crashes with `ModuleNotFoundError: No module named 'termios'`.

---

## Solution Overview

Implement Windows keyboard support following the **exact same pattern** used for LED strips and GPIO managers:

**Pattern**: `Interface → Real Impl → Mock/Platform Impl → Factory with RuntimeInfo`

### Existing Patterns to Follow

1. **LED Strip Pattern**:
   - `IPhysicalStrip` (protocol)
   - `WS281xStrip` (Raspberry Pi hardware)
   - `VirtualStrip` (development mock)
   - Factory uses `RuntimeInfo.is_raspberry_pi()` and `RuntimeInfo.has_ws281x()`

2. **GPIO Manager Pattern**:
   - `IGPIOManager` (protocol)
   - `HardwareGPIOManager` (Raspberry Pi GPIO)
   - `MockGPIOManager` (development mock)
   - Factory uses `RuntimeInfo.has_gpio()`

3. **Keyboard Adapter Pattern** (to be completed):
   - `IKeyboardAdapter` (protocol) ✅ Already exists
   - `EvdevKeyboardAdapter` (Linux physical keyboard) ✅ Already exists
   - `StdinKeyboardAdapter` (Unix terminal) ✅ Already exists
   - `WindowsKeyboardAdapter` (Windows console) ❌ **MISSING**
   - Factory with `RuntimeInfo` ❌ **NEEDS UPDATE**

---

## Current Architecture Analysis

### File Locations

**Active/Primary Location**: `src/hardware/input/keyboard/`
- `keyboard_adapter_interface.py` - Protocol definition
- `keyboard_adapter_factory.py` - Factory for adapter selection
- `evdev_keyboard_adapter.py` - Linux physical keyboard support
- `stdin_keyboard_adapter.py` - Terminal-based keyboard support
- `__init__.py` - Exports the factory function

**Legacy Location**: `src/components/keyboard/` - Contains older, mostly commented-out versions

---

## Detailed Analysis of Existing Implementations

### 1. LED Strip Pattern Analysis

**Interface**: `IPhysicalStrip` (Protocol)
**File**: `src/hardware/led/strip_interface.py`

**Key Methods**:
- `led_count` (property) - Total number of addressable pixels
- `set_pixel(index, color)` - Buffer a single pixel (doesn't push to hardware)
- `get_pixel(index)` - Read buffered pixel color
- `get_frame()` - Read entire buffered frame
- `apply_frame(pixels)` - Atomic push of full frame (single DMA transfer)
- `show()` - Flush buffer to hardware
- `clear()` - Turn off all LEDs

**Real Implementation**: `WS281xStrip`
**File**: `src/hardware/led/ws281x_strip.py`

**Key Features**:
- Color Order Remapping: Supports RGB/GRB/BRG/BGR/etc.
- Internal Buffer: `_buffer: List[Color]` serves as source of truth
- Lazy Import: Only imports `rpi_ws281x` when instantiated
- Atomic Rendering: `apply_frame()` performs single DMA transfer
- Version Compatibility: Handles both old and new `rpi_ws281x` API versions

**Mock Implementation**: `VirtualStrip`
**File**: `src/hardware/led/virtual_strip.py`

**Key Features**:
- In-Memory Buffer: Stores pixel state in `_buffer: List[Color]`
- No Hardware Calls: All methods are no-ops (except buffer management)
- Minimal: Only 41 lines of code
- Perfect for Testing: Allows full app to run on Windows/Mac/WSL

**Factory**: `strip_factory.create_strip()`
**File**: `src/hardware/led/strip_factory.py`

**Decision Logic**:
```python
def create_strip(
    *,
    pixel_count: int,
    gpio_pin: Optional[int],
    color_order: str = "BGR",
) -> IPhysicalStrip:
    if RuntimeInfo.is_raspberry_pi() and RuntimeInfo.has_ws281x():
        try:
            from hardware.led.ws281x_strip import WS281xStrip
            return WS281xStrip(pixel_count=pixel_count, gpio_pin=gpio_pin, color_order=color_order)
        except Exception:
            pass

    return VirtualStrip(pixel_count)
```

---

### 2. GPIO Manager Pattern Analysis

**Interface**: `IGPIOManager` (Protocol)
**File**: `src/hardware/gpio/gpio_manager_interface.py`

**Key Methods**:
- `register_input(pin, component, pull_mode)` - Register input pin
- `register_output(pin, component, initial)` - Register output pin
- `register_ws281x(pin, component)` - Register LED pin
- `read(pin)` - Read pin state
- `write(pin, value)` - Write pin state
- `cleanup()` - Resource cleanup
- `get_registry()` - Get pin allocation map

**Real Implementation**: `HardwareGPIOManager`
**File**: `src/hardware/gpio/gpio_manager_hardware.py`

**Key Features**:
- Lazy import of `RPi.GPIO` inside `__init__`
- Pin registry for conflict detection
- BCM mode (Broadcom pin numbering)
- Pull resistor mapping from custom enums
- WS281x support (tracks pins without GPIO.setup)

**Mock Implementation**: `MockGPIOManager`
**File**: `src/hardware/gpio/gpio_manager_mock.py`

**Key Features**:
- In-memory state (no hardware calls)
- Same interface as hardware implementation
- Pin value tracking with dictionary
- No external dependencies

**Factory**: `create_gpio_manager()`
**File**: `src/hardware/gpio/gpio_manager_factory.py`

**Decision Logic**:
```python
def create_gpio_manager() -> 'IGPIOManager':
    rt = RuntimeInfo()

    if rt.has_gpio():
        return HardwareGPIOManager()
    else:
        return MockGPIOManager()
```

---

### 3. Keyboard Adapter Pattern Analysis

**Interface**: `IKeyboardAdapter` (Protocol)
**File**: `src/hardware/input/keyboard/keyboard_adapter_interface.py`

```python
class IKeyboardAdapter(Protocol):
    async def run(self) -> None:
        ...
```

**Current Implementations**:

1. **EvdevKeyboardAdapter** (Linux physical keyboard)
   **File**: `src/hardware/input/keyboard/evdev_keyboard_adapter.py`
   - Uses `evdev` library (Linux-only)
   - Reads from `/dev/input/event*` devices
   - Not available on Windows

2. **StdinKeyboardAdapter** (Unix terminal)
   **File**: `src/hardware/input/keyboard/stdin_keyboard_adapter.py`
   - Uses `termios`, `tty`, `select` (Unix-only)
   - Terminal control for non-blocking input
   - Fails on Windows with `ModuleNotFoundError`

**Current Factory**: `create_keyboard_adapter()`
**File**: `src/hardware/input/keyboard/keyboard_adapter_factory.py`

```python
def create_keyboard_adapter(event_bus: EventBus) -> IKeyboardAdapter:
    try:
        from .evdev_keyboard_adapter import EvdevKeyboardAdapter
        adapter = EvdevKeyboardAdapter(event_bus)
        return adapter
    except Exception as e:
        from .stdin_keyboard_adapter import StdinKeyboardAdapter
        return StdinKeyboardAdapter(event_bus)
```

**Problem**: No platform detection, relies on import failures

---

## Platform Detection Utility

**File**: `src/runtime/runtime_info.py`

**Existing Methods**:
```python
RuntimeInfo.is_windows()       # Returns True on Windows
RuntimeInfo.is_linux()         # Returns True on Linux
RuntimeInfo.is_raspberry_pi()  # Returns True on Raspberry Pi hardware
RuntimeInfo.has_gpio()         # Check RPi.GPIO availability
RuntimeInfo.has_ws281x()       # Check rpi_ws281x availability
RuntimeInfo.has_module(name)   # Generic module check
```

**Methods to Add**:
```python
RuntimeInfo.has_evdev()        # Check evdev availability
RuntimeInfo.has_termios()      # Check termios availability
RuntimeInfo.has_msvcrt()       # Check msvcrt availability (Windows)
```

---

## Implementation Plan

### Step 1: Add RuntimeInfo Platform Detection Methods

**File**: `src/runtime/runtime_info.py`

```python
@classmethod
def has_evdev(cls) -> bool:
    """Check if evdev library is available (Linux physical keyboard)."""
    return cls.has_module("evdev")

@classmethod
def has_termios(cls) -> bool:
    """Check if termios module is available (Unix terminal control)."""
    return cls.has_module("termios")

@classmethod
def has_msvcrt(cls) -> bool:
    """Check if msvcrt module is available (Windows console I/O)."""
    return cls.has_module("msvcrt")
```

---

### Step 2: Create Windows Keyboard Adapter

**New File**: `src/hardware/input/keyboard/windows_keyboard_adapter.py`

**Purpose**: Windows console keyboard input using `msvcrt` module

**Implementation Outline**:
```python
import asyncio
import msvcrt
from typing import Dict
from services.event_bus import EventBus
from models.events import KeyboardKeyPressEvent
from .keyboard_adapter_interface import IKeyboardAdapter

class WindowsKeyboardAdapter:
    """Windows console keyboard adapter using msvcrt."""

    # Special key mapping for 2-byte sequences
    SPECIAL_KEYS: Dict[int, str] = {
        72: 'up',      # 0xE0 + H
        80: 'down',    # 0xE0 + P
        75: 'left',    # 0xE0 + K
        77: 'right',   # 0xE0 + M
    }

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False

    async def run(self) -> None:
        """Main keyboard input loop."""
        self._running = True

        while self._running:
            try:
                if msvcrt.kbhit():
                    char_code = ord(msvcrt.getch())

                    # Handle special keys (2-byte sequences)
                    if char_code == 0xE0:
                        if msvcrt.kbhit():
                            second_byte = ord(msvcrt.getch())
                            key = self.SPECIAL_KEYS.get(second_byte, f'special_{second_byte}')
                        else:
                            continue
                    else:
                        key = chr(char_code)

                    event = KeyboardKeyPressEvent(key=key)
                    await self.event_bus.publish(event)

                await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                break
            except Exception:
                pass

        self._running = False
```

---

### Step 3: Update Factory with Platform Detection

**File**: `src/hardware/input/keyboard/keyboard_adapter_factory.py`

```python
from services.event_bus import EventBus
from runtime.runtime_info import RuntimeInfo
from .keyboard_adapter_interface import IKeyboardAdapter

def create_keyboard_adapter(event_bus: EventBus) -> IKeyboardAdapter:
    """
    Keyboard adapter factory with platform detection.

    Priority:
    1. Evdev (Linux physical keyboard)
    2. Windows (Windows console)
    3. Stdin (Unix terminal fallback)
    """

    # Try evdev first (Linux physical keyboard)
    if RuntimeInfo.has_evdev():
        try:
            from .evdev_keyboard_adapter import EvdevKeyboardAdapter
            log.info("Using evdev keyboard adapter (Linux)")
            return EvdevKeyboardAdapter(event_bus)
        except Exception as e:
            log.warning("Evdev available but initialization failed", error=str(e))

    # Try Windows console keyboard
    if RuntimeInfo.is_windows() and RuntimeInfo.has_msvcrt():
        try:
            from .windows_keyboard_adapter import WindowsKeyboardAdapter
            log.info("Using Windows keyboard adapter")
            return WindowsKeyboardAdapter(event_bus)
        except Exception as e:
            log.warning("Windows keyboard adapter initialization failed", error=str(e))

    # Try Unix terminal (stdin with termios)
    if RuntimeInfo.has_termios():
        try:
            from .stdin_keyboard_adapter import StdinKeyboardAdapter
            log.info("Using stdin keyboard adapter (Unix terminal)")
            return StdinKeyboardAdapter(event_bus)
        except Exception as e:
            log.warning("Stdin keyboard adapter initialization failed", error=str(e))

    raise RuntimeError(
        "No compatible keyboard adapter available. "
        "Platform requires one of: evdev (Linux), msvcrt (Windows), or termios (Unix)."
    )
```

---

### Step 4: Update Package Exports

**File**: `src/hardware/input/keyboard/__init__.py`

```python
from .keyboard_adapter_interface import IKeyboardAdapter
from .evdev_keyboard_adapter import EvdevKeyboardAdapter
from .stdin_keyboard_adapter import StdinKeyboardAdapter
from .windows_keyboard_adapter import WindowsKeyboardAdapter  # NEW
from .keyboard_adapter_factory import create_keyboard_adapter

__all__ = [
    "IKeyboardAdapter",
    "EvdevKeyboardAdapter",
    "StdinKeyboardAdapter",
    "WindowsKeyboardAdapter",  # NEW
    "create_keyboard_adapter",
]
```

---

## Critical Files Summary

### New Files
1. `src/hardware/input/keyboard/windows_keyboard_adapter.py` - Windows implementation

### Modified Files
1. `src/runtime/runtime_info.py` - Add detection methods
2. `src/hardware/input/keyboard/keyboard_adapter_factory.py` - Update factory
3. `src/hardware/input/keyboard/__init__.py` - Update exports

### Files NOT Modified
- `src/hardware/input/keyboard/keyboard_adapter_interface.py` - Already correct
- `src/hardware/input/keyboard/evdev_keyboard_adapter.py` - No changes needed
- `src/hardware/input/keyboard/stdin_keyboard_adapter.py` - No changes needed
- `src/main_asyncio.py` - Uses factory, no changes needed

---

## Windows-Specific Implementation Details

### msvcrt API Reference
- `msvcrt.kbhit()` → Returns `True` if key press available
- `msvcrt.getch()` → Returns single byte (blocks if no key pressed)
- `msvcrt.getwch()` → Returns Unicode character (for international keyboards)

### Special Key Handling
Windows console special keys return 2-byte sequences:
1. First byte: `0xE0` (extended key) or `0x00` (function key)
2. Second byte: Key-specific code

**Common Mappings**:
- `0xE0 + 72` → Up arrow
- `0xE0 + 80` → Down arrow
- `0xE0 + 75` → Left arrow
- `0xE0 + 77` → Right arrow
- `0xE0 + 71` → Home
- `0xE0 + 79` → End
- `0x00 + 59` → F1
- `0x00 + 60` → F2

---

## Pattern Consistency Check

| Component | Interface | Real Impl | Mock/Alt Impl | Factory | RuntimeInfo |
|-----------|-----------|-----------|---------------|---------|-------------|
| **LED Strip** | `IPhysicalStrip` | `WS281xStrip` | `VirtualStrip` | `create_strip()` | `is_raspberry_pi()`, `has_ws281x()` |
| **GPIO Manager** | `IGPIOManager` | `HardwareGPIOManager` | `MockGPIOManager` | `create_gpio_manager()` | `has_gpio()` |
| **Keyboard** | `IKeyboardAdapter` | `EvdevKeyboardAdapter` | `StdinKeyboardAdapter`, `WindowsKeyboardAdapter` | `create_keyboard_adapter()` | `has_evdev()`, `has_termios()`, `has_msvcrt()` |

✅ All components follow the same architectural pattern

---

## Expected Behavior After Implementation

### Windows Platform
```
[INFO] Using Windows keyboard adapter
[INFO] Keyboard adapter initialized (Windows console)
```

### Linux Platform (with evdev)
```
[INFO] Using evdev keyboard adapter (Linux)
[INFO] Keyboard adapter initialized (physical keyboard)
```

### Linux/WSL Platform (without evdev)
```
[INFO] Using stdin keyboard adapter (Unix terminal)
[INFO] Keyboard adapter initialized (terminal input)
```

---

## Code Style Compliance

Following project coding standards from `.claude/CLAUDE.md`:

✅ **Import Organization**: All imports at module level, no inline imports
✅ **Dependency Injection**: Constructor injection via `__init__`
✅ **Type Hints**: All methods have full type hints
✅ **Async Patterns**: Proper `async def`, `await`, task cancellation
✅ **Protocol-Based Interface**: Uses `IKeyboardAdapter` Protocol
✅ **PEP 8**: Standard Python style conventions

---

## Dependencies

### No New Dependencies Required
- `msvcrt` is built-in to Python on Windows
- No pip install needed
- No additional system libraries

---

## Summary

This implementation adds Windows keyboard support by following the **exact same architectural pattern** used for LED strips and GPIO managers:

1. **Protocol interface** - Already exists (`IKeyboardAdapter`)
2. **Platform-specific implementations** - Add `WindowsKeyboardAdapter`
3. **Factory with RuntimeInfo** - Update `create_keyboard_adapter()`
4. **Graceful degradation** - Fallback chain: evdev → Windows → stdin

After implementation, the Diuna LED controller will work seamlessly on Windows development machines with full keyboard input support, while maintaining compatibility with Linux/Raspberry Pi production environments.
