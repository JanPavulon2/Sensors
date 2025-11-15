---
Last Updated: 2025-11-15
Created By: Migration from CLAUDE.md
Purpose: Code style and conventions
---

# Coding Standards

## Critical Rules

**ALWAYS**:
- Use enums instead of magic strings
- Add type hints to all functions
- Use asyncio for long-running operations (NEVER blocking sleep/IO)
- Import at module level (NO inline imports)
- Use constructor injection (NO property assignment)
- Add logging for state changes and errors

**NEVER**:
- Use magic strings/numbers
- Silent error catching (`except: pass`)
- Block asyncio event loop (`time.sleep()`)
- Recommend non-Raspberry Pi solutions
- Access state.json directly (use DataAssembler)

## Code Quality Examples

### ✅ Good: Enums
```python
from models.enums import MainMode
mode = MainMode.STATIC
```

### ❌ Bad: Magic Strings
```python
mode = "static"  # Typos not caught
```

### ✅ Good: Type Hints
```python
def set_color(self, zone_id: ZoneID, color: Color) -> None:
    zone: ZoneCombined = self._by_id[zone_id]
```

### ❌ Bad: No Types
```python
def set_color(self, zone_id, color):
    zone = self._by_id[zone_id]
```

## Architecture Rules

**Domain Models**: Use Config + State + Combined pattern
```python
@dataclass(frozen=True)
class ZoneConfig: ...  # Immutable from YAML

@dataclass
class ZoneState: ...    # Mutable from JSON

class ZoneCombined:     # Aggregate root
    def __init__(self, config: ZoneConfig, state: ZoneState): ...
```

**Services**: Coordinate domain objects + handle persistence
```python
class ZoneService:
    def set_color(self, zone_id: ZoneID, color: Color):
        zone.state.color = color
        self.save()  # Auto-save via DataAssembler
```

**Repository**: Only DataAssembler reads/writes state.json
```python
# ❌ WRONG
with open('state.json') as f: ...

# ✅ CORRECT
assembler.save_zone_state(zones)
```

## File Organization

**Imports**: Module-level only
```python
# ✅ CORRECT
from models.enums import MainMode

def some_function():
    mode = MainMode.STATIC

# ❌ WRONG
def some_function():
    from models.enums import MainMode  # NO inline imports
```

**Dependency Injection**: Constructor-based
```python
# ✅ CORRECT
def __init__(self, frame_manager: FrameManager):
    self.frame_manager = frame_manager

# ❌ WRONG
service.frame_manager = frame_manager  # NO property injection
```

## Logging

Two ways of using logger: 
- General logger when file logs information from multiple
```python
from utils.logger import get_logger, LogCategory

log = get_logger()
log.info(LogCategory.ZONE, "Zone changed", param)
log.error(LogCategory.SYSTEM, "Animation failed", e)
```

- Category logger when file logs information mostly from one area. Set area becomes default value for LogCategory parameter. However, it's possible to override it.
```python
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.RENDER_ENGINE)
log.info("Render engine initialized")
log.info(LogCategory.SYSTEM, "Override category and log as system")
```

## Documentation

**Docstrings**: Required for public methods
```python
def set_zone_color(self, zone_id: str, r: int, g: int, b: int, show: bool = True):
    """
    Set uniform color for zone.
    
    Args:
        zone_id: Zone identifier (e.g., "LAMP")
        r, g, b: RGB values (0-255)
        show: Call strip.show() immediately
    """
```

**Comments**: Explain WHY, not WHAT
```python
# CRITICAL: Recalculate INSIDE loop for live parameter updates
frame_delay = self._calculate_frame_delay()
```

