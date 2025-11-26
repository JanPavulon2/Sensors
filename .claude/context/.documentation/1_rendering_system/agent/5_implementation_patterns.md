---
Last Updated: 2025-11-25
Type: Agent Documentation
Purpose: Implementation patterns and code conventions
---

# Implementation Patterns

## Dependency Injection

**Pattern**: Constructor injection only, never property assignment.

✅ CORRECT:
```python
class MyController:
    def __init__(self, frame_manager: FrameManager, zone_service: ZoneService):
        self.frame_manager = frame_manager
        self.zone_service = zone_service

    async def do_something(self):
        # Use injected dependencies
        await self.frame_manager.submit_zone_frame(...)
```

❌ WRONG:
```python
class MyController:
    async def init(self):
        # Property injection - wrong!
        self.frame_manager = get_frame_manager()

    def __init__(self):
        pass  # Dependencies not clear
```

**Why**:
- Constructor declares dependencies clearly
- Dependencies testable (can mock)
- Impossible to use uninitialized attributes
- Type hints work correctly

## Type Checking for Circular Imports

**Pattern**: Use `TYPE_CHECKING` to break circular dependencies.

✅ CORRECT:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from managers import ColorManager

class Color:
    @classmethod
    def from_preset(cls, name: str, color_manager: 'ColorManager') -> 'Color':
        # Use string literal for type hint
        # ColorManager not imported at runtime
        pass
```

❌ WRONG:
```python
from managers import ColorManager  # Circular import!

class Color:
    @classmethod
    def from_preset(cls, name: str, color_manager: ColorManager) -> 'Color':
        pass
```

**Why**:
- Avoids circular import errors
- Type hints still work (with mypy, IDE)
- Runtime works without import issues
- Clear that import is only for type checking

## Async/Await Patterns

**Always await async calls**:
```python
# CORRECT
await animation_engine.start(anim_id)
result = await frame_manager.submit_zone_frame(frame)

# WRONG - missing await!
animation_engine.start(anim_id)  # Doesn't actually run
```

**Use asyncio.create_task() for fire-and-forget**:
```python
# Start task without waiting
task = asyncio.create_task(self._pulse_task())

# Remember to cancel in cleanup
async def cleanup(self):
    if self._pulse_task and not self._pulse_task.done():
        self._pulse_task.cancel()
```

**Use async context managers**:
```python
async with some_resource as resource:
    # Resource auto-cleaned up after block
    await resource.do_something()
```

**Use asyncio.sleep() not time.sleep()**:
```python
# CORRECT - doesn't block event loop
await asyncio.sleep(0.1)

# WRONG - blocks event loop!
import time
time.sleep(0.1)
```

## Type Hints

**All functions must have return type hints**:
```python
# CORRECT
async def submit_frame(self, frame: ZoneFrame) -> None:
    ...

def get_zone_count(self) -> int:
    return len(self.zones)

# WRONG - missing return type
async def submit_frame(self, frame: ZoneFrame):
    ...
```

**All class attributes must have type hints**:
```python
# CORRECT
class Controller:
    frame_manager: FrameManager
    zones: List[Zone]
    enabled: bool = True

    def __init__(self, fm: FrameManager):
        self.frame_manager = fm
        self.zones = []

# WRONG - attributes not typed
class Controller:
    def __init__(self, fm):
        self.frame_manager = fm
        self.zones = []
```

## Enum Usage

**Always use enums, never magic strings**:
```python
# CORRECT
zone_id = ZoneID.FLOOR
animation_id = AnimationID.BREATHE
color_order = ColorOrder.BGR

# WRONG - magic strings
zone_id = "floor"
animation_id = "breathe"
color_order = "BGR"
```

**Why**:
- Type-safe (mypy catches errors)
- IDE autocomplete works
- Refactoring finds all uses
- No typos possible

## Frame Submission Pattern

**All rendering through FrameManager**:
```python
# Create frame
frame = ZoneFrame(zones={zone_id: color}, priority=MANUAL)

# Submit to FrameManager
await frame_manager.submit_zone_frame(frame)

# NEVER call hardware directly!
# NEVER call strip.show()
# NEVER manipulate pixels directly
```

## Color Handling

**Always use Color class, never tuples**:
```python
# CORRECT
color = Color(red=255, green=100, blue=50)
dark_color = color.with_brightness(0.5)
red = color.red
r, g, b = color.to_rgb()

# WRONG - tuples
color = (255, 100, 50)
r, g, b = color  # What order? RGB or BGR?
```

## Animation Generator Pattern

**Animations are infinite generators**:
```python
async def my_animation(zone_id: ZoneID, speed: int, color: Color):
    """Animation generator."""
    while True:
        # Compute frame for this moment
        brightness = compute_brightness_from_time(speed)
        adjusted_color = color.with_brightness(brightness)

        # Yield frame data
        yield (zone_id, adjusted_color)

        # Wait for next frame (60 FPS)
        await asyncio.sleep(1/60)
```

**Don't yield raw values**:
```python
# CORRECT
yield (zone_id, Color(...))

# WRONG - raw RGB tuple
yield (zone_id, (255, 100, 50))
```

## Naming Conventions

**No abbreviations**:
```python
# CORRECT
frame_manager = FrameManager()
animation_engine = AnimationEngine()
pixel_count = 51

# WRONG - abbreviations
fm = FrameManager()
ae = AnimationEngine()
px_cnt = 51
```

**Descriptive names**:
```python
# CORRECT
get_zone_pixel_indices(zone_id)
submit_all_zones_frame(zones_colors)
update_parameter(parameter_id, value)

# WRONG - vague names
get_pixels(z)
submit_frame(data)
update(p, v)
```

## Error Handling

**Catch specific exceptions**:
```python
# CORRECT
try:
    await frame_manager.submit_zone_frame(frame)
except ValueError as e:
    logger.error(f"Invalid frame: {e}")
    return

# WRONG - catches everything
try:
    await frame_manager.submit_zone_frame(frame)
except:
    pass  # Silently fails
```

**Log useful context**:
```python
# CORRECT
logger.error(f"Animation failed: {animation_id}, error: {e}", exc_info=True)

# WRONG - no context
logger.error("Error")
```

## Testing Patterns

**Mock dependencies for testing**:
```python
# With mocks
mock_fm = Mock(spec=FrameManager)
controller = MyController(frame_manager=mock_fm)
await controller.do_something()
mock_fm.submit_zone_frame.assert_called_once()

# NOT testing against real hardware
```

**Test at appropriate layer**:
```python
# Test animation generator in isolation
gen = my_animation(FLOOR, 50, red_color)
frame1 = await gen.asend(None)
frame2 = await gen.asend(None)
assert frame1 != frame2  # Changes over time

# Test controller logic separately
# Test FrameManager logic separately
# Integration tests combine pieces
```

## Code Organization

**Flat main() function**:
```python
# CORRECT - flat, readable
async def main():
    logger.info("Loading configuration...")
    config_manager = ConfigManager()
    config_manager.load()

    logger.info("Initializing FrameManager...")
    frame_manager = FrameManager()

    logger.info("Creating controllers...")
    controllers = _create_controllers(...)

    logger.info("Starting event loop...")
    await _run_event_loop(controllers, frame_manager)
```

**Not nested logic in main()**:
```python
# WRONG - main has embedded logic
async def main():
    config_manager = ConfigManager()
    config_manager.load()
    for controller_type in [StaticMode, AnimationMode, ...]:
        # Nested logic in main
        ...
```

## Documentation Comments

**Use docstrings for public methods**:
```python
async def submit_zone_frame(self, frame: ZoneFrame) -> None:
    """Submit a zone frame for rendering.

    Args:
        frame: ZoneFrame with zones and colors

    Raises:
        ValueError: If frame is invalid
    """
    ...
```

**Not inline comments for obvious code**:
```python
# WRONG
x = y + 1  # Add 1 to y

# CORRECT (if needed)
# Calculate next animation frame index
frame_index = current_index + 1
```

---

**Summary**: Follow these patterns for clean, maintainable, testable code.
