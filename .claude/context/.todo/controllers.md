---
Last Updated: 2025-11-25
Title: Controller Tasks and Improvements
Category: Controllers
---

# Controllers TODO

## Active Controllers Status

### ✅ Fully Functional (7 Controllers)
1. **LEDController** - Main orchestrator ✅
2. **StaticModeController** - Zone editing ✅
3. **AnimationModeController** - Animations ✅
4. **ZoneStripController** - Rendering ✅
5. **PowerToggleController** - Power management ✅
6. **LampWhiteModeController** - Lamp mode ✅
7. **ControlPanelController** - Hardware input ✅

### ✅ Implemented, Needs Testing (1 Controller)
8. **FramePlaybackController** - Frame-by-frame debugging
   - Status: Code complete, untested
   - Issue: Needs keyboard event integration testing
   - Priority: LOW (debugging feature)

### ⚠️ Disabled, Needs Integration (1 Controller)
9. **PreviewPanelController** - Preview visualization
   - Status: Disabled in main_asyncio.py:237-259
   - Issue: Not integrated with FrameManager
   - Needs: PreviewService implementation
   - Priority: MEDIUM (user feature)

---

## Code Quality Improvements

### Controller Naming Review

**Current Status**: ✅ All naming consistent
- All controllers end with `Controller` suffix
- No abbreviations used
- Clear, descriptive names

**Example Good Names**:
- `StaticModeController` (not `StaticCtrl` or `ColorCtrl`)
- `AnimationModeController` (not `AnimCtrl`)
- `PowerToggleController` (not `PowerCtrl`)

---

## DRY Violations in Controllers

### 1. Color Conversion Repetition

**Files**: `static_mode_controller.py`, `zone_strip_controller.py`
**Priority**: LOW
**Time**: 30 minutes

**Current Pattern**:
```python
# Repeated in multiple controllers
r, g, b = color.to_rgb()
r, g, b = Color.apply_brightness(r, g, b, brightness)
```

**Solution**:
```python
# In Color class
def to_rgb_with_brightness(self, brightness: float) -> Tuple[int, int, int]:
    r, g, b = self.to_rgb()
    return (int(r * brightness), int(g * brightness), int(b * brightness))

# Then in controllers
r, g, b = color.to_rgb_with_brightness(zone.brightness)
```

**Affected Controllers**:
- `StaticModeController` (line ~80)
- `ZoneStripController` (line ~100)

---

### 2. Excluded Zones List Building

**Files**: `animation_mode_controller.py`, `led_controller.py`
**Priority**: LOW
**Time**: 15 minutes

**Current Pattern**:
```python
# Repeated exclusion list building
excluded_zones = [
    zone.config.id for zone in self.zone_service.get_all()
    if zone.config.id != selected_zone.config.id
]
```

**Solution**:
```python
# In ZoneService
def get_excluded_zones(self, except_zone_id: ZoneID) -> List[ZoneID]:
    return [z.config.id for z in self.get_all() if z.config.id != except_zone_id]

# Then in controllers
excluded_zones = self.zone_service.get_excluded_zones(selected_zone.config.id)
```

**Affected Controllers**:
- `AnimationModeController` (line ~100)
- `LEDController` (line ~200)

---

### 3. Parameter Adjustment Pattern

**Files**: Multiple controllers
**Priority**: LOW
**Time**: 1 hour (if extracting)

**Current Pattern**:
```python
# Repeated in animation_mode_controller, static_mode_controller
async def adjust_param(self, param_id, delta):
    if param_id == ParameterID.SPEED:
        self.speed = clamp(self.speed + delta, 1, 100)
        await self.service.update_parameter('speed', self.speed)
    elif param_id == ParameterID.INTENSITY:
        # Similar pattern
```

**Note**: This pattern is acceptable for now. Extraction would require reflection/dispatch pattern. Only extract if many more parameters added.

---

## Controller Relationships Verification

### Dependency Graph ✅

**Verified relationships**:
- LEDController → owns AnimationEngine ✅
- LEDController → routes to mode controllers ✅
- StaticModeController → uses ZoneStripController ✅
- AnimationModeController → uses AnimationEngine ✅
- ZoneStripController → submits to FrameManager ✅
- PowerToggleController → uses TransitionService ✅
- ControlPanelController → publishes events ✅

**Circular dependency check**: ✅ CLEAN
- No circular imports found
- TYPE_CHECKING used correctly
- Clean layering maintained

---

## Keyboard Event Integration

### FramePlaybackController Testing

**Status**: Code exists but untested
**File**: `src/controllers/led_controller/frame_playback_controller.py`
**Task**: Verify keyboard events trigger controller correctly

**Keyboard Mappings**:
- `A` - Previous frame
- `D` - Next frame
- `SPACE` - Play/pause
- `Q` - Quit playback mode

**Testing Needed**:
1. Start frame playback mode
2. Verify keyboard events detected
3. Confirm frame navigation works
4. Check play/pause toggle
5. Verify log output correct

**Estimated Time**: 2-3 hours (setup + testing)

---

## Mode-Specific Controller Analysis

### Per-Zone Mode Handling

**Question**: Do we still need both StaticModeController and AnimationModeController after switching to per-zone modes?

**Answer**: YES ✅
- Each zone can independently be STATIC or ANIMATION
- StaticModeController handles STATIC zones
- AnimationModeController handles ANIMATION zones
- LEDController routes to correct controller based on selected zone's mode

**Example Flow**:
```
User selects FLOOR (currently in STATIC mode)
  ↓
User rotates encoder
  ↓
LEDController checks: FLOOR.mode == STATIC?
  ↓
Routes to StaticModeController.adjust_hue()
  ↓
FLOOR color changes

User toggles mode → FLOOR.mode = ANIMATION
  ↓
User rotates encoder
  ↓
LEDController checks: FLOOR.mode == ANIMATION?
  ↓
Routes to AnimationModeController.adjust_param()
  ↓
Animation parameter changes
```

**Naming Verification**:
- `StaticModeController` - correct (handles STATIC mode)
- `AnimationModeController` - correct (handles ANIMATION mode)
- ✅ Names accurately reflect responsibilities

---

## Design Pattern Consistency

### Dependency Injection

**Verified**: ✅ CORRECT
- All controllers use constructor injection
- No property injection found
- All dependencies injected in `__init__`

### Type Hints

**Verified**: ✅ CORRECT
- All methods have return type hints
- All parameters typed
- No `Any` types found

### Async Patterns

**Verified**: ✅ CORRECT
- All async methods properly awaited
- asyncio.create_task() used for fire-and-forget
- Proper cleanup in shutdown

---

## Testing Recommendations

### Unit Tests Needed
- StaticModeController: Color adjustment tests
- AnimationModeController: Parameter update tests
- ZoneStripController: Frame submission tests
- PowerToggleController: Fade transition tests

**Estimated Time**: 3-5 hours for test suite

---

## Task Summary

| Task | Priority | Time | Status |
|------|----------|------|--------|
| Review controller naming | 🟢 LOW | - | ✅ COMPLETE |
| Verify dependency injection | 🟢 LOW | - | ✅ COMPLETE |
| Color conversion refactor | 🟢 LOW | 30m | PENDING |
| Excluded zones helper | 🟢 LOW | 15m | PENDING |
| FramePlaybackController testing | 🟢 LOW | 2-3h | PENDING |
| PreviewPanel integration | 🟡 MEDIUM | 3-4h | PENDING |
| Unit test suite | 🟡 MEDIUM | 3-5h | PENDING |

---

## Verification Checklist

- ✅ All 9 controllers identified and analyzed
- ✅ 7 controllers fully active
- ✅ 1 controller (FramePlayback) implemented, needs testing
- ✅ 1 controller (PreviewPanel) needs integration
- ✅ Naming conventions correct
- ✅ Dependency injection verified
- ✅ No circular dependencies
- ✅ Async patterns correct
- ✅ Type hints complete
- ✅ Mode routing logic verified

---

**Last Updated**: 2025-11-25
**Next Review**: After PreviewPanel integration complete

---

## Related Documentation
- See `../rendering_system.md` for rendering system tasks
- See `../project/todo.md` for overall project status
- See `.documentation/1_rendering_system/agent/3_controller_relationships.md` for detailed controller info
