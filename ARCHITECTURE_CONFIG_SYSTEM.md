# Configuration System Architecture

## 🎯 Design Principles

### Single Responsibility Principle (SRP)
- **ConfigManager**: File I/O + include system
- **Sub-managers**: Data processing only (no file access)
- **LEDController**: Business logic only (no config loading)

### Dependency Injection
- ConfigManager creates all sub-managers
- LEDController receives ConfigManager (not raw dicts)
- Sub-managers receive processed data (not file paths)

### Single Source of Truth
- ConfigManager is the **ONLY** component that loads files
- All config flows through `ConfigManager.load()`
- No parallel loading paths

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       main_asyncio.py                       │
│                    (Application Entry)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
          ┌────────────────────────┐
          │   ConfigManager.load() │  ← SINGLE ENTRY POINT
          │                        │
          │  Loads ALL YAML files  │
          │  via include system    │
          └────────┬───────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
   ┌─────────┐         ┌──────────┐
   │ YAML    │         │ YAML     │
   │ Files   │         │ Files    │
   └─────────┘         └──────────┘
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  Merged Config Dict  │
        └──────────┬───────────┘
                   │
       ┌───────────┼───────────┬───────────────┐
       │           │           │               │
       ▼           ▼           ▼               ▼
   ┌────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
   │Hardware│ │  Zone   │ │Animation │ │  Color   │
   │Manager │ │ Manager │ │ Manager  │ │ Manager  │
   └────┬───┘ └────┬────┘ └────┬─────┘ └────┬─────┘
        │          │           │             │
        └──────────┴───────────┴─────────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │   LEDController     │  ← Receives ConfigManager
                │                     │
                │ (Business Logic)    │
                └─────────────────────┘
```

---

## 🔄 Data Flow

### Startup Sequence

```python
# 1. Create ConfigManager
config_manager = ConfigManager()
config_manager.load()  # ← Loads ALL config + creates sub-managers

# 2. ConfigManager.load() internal flow:
#    a) Load config.yaml
#    b) Process include: [hardware.yaml, zones.yaml, colors.yaml, ...]
#    c) Merge all YAMLs into single dict
#    d) Create sub-managers with data injection:
#       - HardwareManager(merged_data)
#       - ZoneManager(zones_list)
#       - ColorManager({'presets': ..., 'preset_order': ...})
#       - AnimationManager(merged_data)

# 3. Create LEDController with ConfigManager
led = LEDController(config_manager, state)

# 4. LEDController accesses managers via dependency injection:
led.color_manager = config_manager.color_manager  # Already loaded!
led.animation_manager = config_manager.animation_manager  # Already loaded!
```

---

## 📁 Component Responsibilities

### ConfigManager
**Responsibility**: File I/O + Manager Factory

```python
class ConfigManager:
    def load():
        """
        1. Load config.yaml
        2. Process include: directive
        3. Merge all YAMLs
        4. Create sub-managers with data
        5. Return self (fluent interface)
        """

    @property
    def hardware_manager: HardwareManager  # Already created

    @property
    def zone_manager: ZoneManager  # Already created

    @property
    def color_manager: ColorManager  # Already created

    @property
    def animation_manager: AnimationManager  # Already created
```

**Does**:
- ✅ Load YAML files
- ✅ Merge configs
- ✅ Create sub-managers
- ✅ Provide access to sub-managers

**Does NOT**:
- ❌ Parse hardware details (delegates to HardwareManager)
- ❌ Calculate zone indices (delegates to ZoneManager)
- ❌ Process color presets (delegates to ColorManager)

---

### Sub-Managers (HardwareManager, ZoneManager, ColorManager, AnimationManager)
**Responsibility**: Data Processing Only

```python
class ColorManager:
    def __init__(self, data: dict):  # ← Receives data, not file path
        """
        Process color preset data

        Args:
            data: {'presets': {...}, 'preset_order': [...]}
        """
        self._process_data()  # Parse and cache

    def get_preset_rgb(self, name: str) -> Tuple[int, int, int]:
        """Access processed data"""
```

**Does**:
- ✅ Parse data structures
- ✅ Build caches
- ✅ Provide typed access methods
- ✅ Validate data

**Does NOT**:
- ❌ Load files
- ❌ Know about file paths
- ❌ Merge configs
- ❌ Create other managers

---

### LEDController
**Responsibility**: Business Logic + Hardware Control

```python
class LEDController:
    def __init__(self, config_manager: ConfigManager, state: dict):
        """
        Receives ConfigManager (dependency injection)

        Args:
            config_manager: Provides access to all config + sub-managers
            state: Runtime state from state.json
        """
        # Access managers via dependency injection
        self.color_manager = config_manager.color_manager
        self.animation_manager = config_manager.animation_manager

        # Access hardware config via manager
        hardware_manager = config_manager.hardware_manager
        preview_config = hardware_manager.get_led_strip("preview")
```

**Does**:
- ✅ Control LEDs (business logic)
- ✅ Manage state machine
- ✅ Handle user input
- ✅ Use managers for config access

**Does NOT**:
- ❌ Load config files
- ❌ Create managers
- ❌ Parse YAML
- ❌ Merge configs

---

## 🚫 Anti-Patterns (What We Eliminated)

### ❌ OLD: Dual Loading Paths
```python
# BAD: Two ways to load config
config_manager = ConfigManager()
config_manager.load()  # Path 1: Include system

color_manager = ColorManager()  # Path 2: Loads colors.yaml directly ❌
```

### ❌ OLD: Sub-Managers Load Files
```python
# BAD: ColorManager knows about file system
class ColorManager:
    def __init__(self):
        self.load()  # Loads config/colors.yaml ❌

    def load(self):
        with open("config/colors.yaml") as f:  # ❌ File I/O in business logic
            self.data = yaml.safe_load(f)
```

### ❌ OLD: LEDController Creates Managers
```python
# BAD: LEDController creates its own managers
class LEDController:
    def __init__(self, config: dict, state: dict):
        self.color_manager = ColorManager()  # ❌ Creates instead of receives
        self.animation_manager = AnimationManager()  # ❌ Tight coupling
```

---

## ✅ New Patterns (What We Implemented)

### ✅ NEW: Single Loading Path
```python
# GOOD: One entry point
config_manager = ConfigManager()
config_manager.load()  # Only place that loads files ✅

# All managers already created internally
led = LEDController(config_manager, state)
```

### ✅ NEW: Sub-Managers Process Data Only
```python
# GOOD: ColorManager receives data
class ColorManager:
    def __init__(self, data: dict):  # ✅ Receives processed data
        self._process_data()  # Only parsing, no I/O

    def _process_data(self):
        # Cache RGB values, identify whites, etc.
        # NO file operations ✅
```

### ✅ NEW: Dependency Injection
```python
# GOOD: LEDController receives managers
class LEDController:
    def __init__(self, config_manager: ConfigManager, state: dict):
        # Managers injected via config_manager ✅
        self.color_manager = config_manager.color_manager
        self.animation_manager = config_manager.animation_manager
```

---

## 🧪 Testing Benefits

### Before (Hard to Test)
```python
# Had to mock file system for every test
@patch('builtins.open', mock_open(read_data='...'))
def test_color_manager():
    cm = ColorManager()  # Loads file internally ❌
```

### After (Easy to Test)
```python
# Just pass test data
def test_color_manager():
    test_data = {'presets': {'red': {'rgb': [255, 0, 0]}}, 'preset_order': ['red']}
    cm = ColorManager(test_data)  # No file I/O ✅
    assert cm.get_preset_rgb('red') == (255, 0, 0)
```

---

## 📦 File Structure

```
src/
├── main_asyncio.py           ← Entry point (creates ConfigManager)
├── led_controller.py          ← Business logic (receives ConfigManager)
├── managers/
│   ├── config_manager.py     ← ONLY file loader (factory for sub-managers)
│   ├── hardware_manager.py   ← Data processor (no file I/O)
│   ├── zone_manager.py       ← Data processor (no file I/O)
│   ├── color_manager.py      ← Data processor (no file I/O)
│   └── animation_manager.py  ← Data processor (no file I/O)
└── config/
    ├── config.yaml            ← Include system entry
    ├── hardware.yaml          ← Hardware definitions
    ├── zones.yaml             ← Zone definitions
    ├── colors.yaml            ← Color presets
    ├── animations.yaml        ← Animation metadata
    └── parameters.yaml        ← Parameter definitions
```

---

## 🎓 Key Takeaways

1. **Single Entry Point**: `ConfigManager.load()` is the ONLY place that touches the file system
2. **Dependency Injection**: Managers receive data, not file paths
3. **Separation of Concerns**: File I/O ≠ Data Processing ≠ Business Logic
4. **Testability**: Data processors can be tested without mocking files
5. **Maintainability**: Clear responsibilities make code easier to understand

---

## 🚀 Future Enhancements

### Potential Improvements

1. **Config Validation**: Add JSON schema validation for YAML files
2. **Hot Reload**: Watch YAML files and reload on change
3. **Config Profiles**: Support multiple config sets (dev, prod, test)
4. **Lazy Loading**: Load sub-managers only when accessed
5. **Config API**: Expose config via REST/WebSocket for remote management

### Architecture is Ready For

- ✅ Multiple config sources (files, database, API)
- ✅ Config caching
- ✅ Config versioning
- ✅ A/B testing (different configs for different zones)

---

**Last Updated**: 2025-01-22
**Architecture Status**: ✅ Production Ready
**SOLID Compliance**: ✅ Full
