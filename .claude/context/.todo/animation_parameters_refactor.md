# TODO: Animation Parameters System Refactor

**Status:** DEFERRED - Do after render mode switching implementation
**Priority:** MEDIUM
**Estimated Effort:** 13-17 hours (2-3 days)

## Problem Summary

Animation parameters system has good architectural foundation (type-safe classes) but incomplete implementation:
- ❌ `parameters.yaml` - defined but NOT loaded by code
- ❌ `state.json` - `"parameters": {}` always empty
- ❌ State persistence broken - user changes not saved
- ⚠️ Naming inconsistencies: `SPEED` vs `ANIM_SPEED`
- ⚠️ Pattern inconsistencies: inline `IntRangeParam` vs typed `LengthParam`

## Impact

Users CANNOT customize animations - always use hardcoded defaults.

## Recommended Solution

**Option C: Unified Class-First System**
- Python classes = single source of truth
- YAML only for optional UI metadata
- Fix state persistence
- Add validation

## Implementation Phases

### Phase 1: Fix State Persistence (HIGH PRIORITY)
**Effort:** 2-3 hours | **Risk:** LOW

Files to modify:
- `src/services/animation_service.py` - populate defaults in `build_params_for_zone()`
- `src/services/zone_service.py` - add `set_animation_param()` method
- Test: parameter changes persist across restarts

### Phase 2: Standardize Parameter Classes (MEDIUM PRIORITY)
**Effort:** 3-4 hours | **Risk:** LOW

- Create `StandardParams` library
- Migrate all animations to use standard params
- Remove inline `IntRangeParam()` constructions

### Phase 3: Add Validation (MEDIUM PRIORITY)
**Effort:** 3-4 hours | **Risk:** MEDIUM

- `AnimationState.set_parameter()` with validation
- Check param is supported by animation
- API-level validation

### Phase 4: Clean Up YAML (LOW PRIORITY)
**Effort:** 1 hour | **Risk:** LOW

- Remove unused `animation_base_parameters` from `parameters.yaml`
- Add comments explaining params are in code

### Phase 5: API Integration (LOW PRIORITY)
**Effort:** 4-5 hours | **Risk:** MEDIUM

- `GET /zones/{id}/animation/parameters`
- `PATCH /zones/{id}/animation/parameters`
- WebSocket notifications

## Key Architecture Decisions

1. **Class-first approach:** Animation classes define parameters via `PARAMS` dict
2. **Naming convention:** `AnimationParamID.SPEED` (no `ANIM_` prefix)
3. **Multi-layer validation:** Type → Assignment → API
4. **Default resolution order:** User state → Animation defaults → Parameter defaults

## Code Example

```python
# Standard parameter library
class StandardParams:
    SPEED = SpeedParam()                    # 1-100, default 50
    BRIGHTNESS = BrightnessParam()          # 0-100, default 100
    PRIMARY_HUE = PrimaryColorHueParam()    # 0-359, default 30
    LENGTH_MEDIUM = LengthParam(1, 20, 5)

# Animation uses standard params
class BreatheAnimation(BaseAnimation):
    PARAMS = {
        AnimationParamID.SPEED: StandardParams.SPEED,
        AnimationParamID.BRIGHTNESS: StandardParams.BRIGHTNESS,
    }

    DEFAULT_PARAMS = {
        AnimationParamID.SPEED: 40,  # Override default
    }

# Service populates defaults + user overrides
def build_params_for_zone(...):
    params = {}

    # 1. Class defaults
    for param_id, param_def in anim_class.PARAMS.items():
        params[param_id] = param_def.default

    # 2. User state (from state.json)
    params.update(zone_animation_params)

    # 3. Zone context
    params[COLOR] = zone.color

    return params
```

## Full Analysis

See detailed analysis report from architecture-expert-sonnet (2025-12-30).
Complete audit of all animations, parameters, inconsistencies, and migration strategy.

---

**NEXT STEP WHEN READY:** Start with Phase 1 (fix state persistence) - 2-3 hours, highest ROI
