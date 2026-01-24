# SnapshotPublisher Refactoring Plan: Type Safety & Event Architecture

## Executive Summary

The `SnapshotPublisher` component has critical architectural flaws that violate type safety, create phantom event subscriptions, and use anti-patterns that defeat Python's type system. This refactoring will fix these issues while maintaining backward compatibility.

---

## Complete Problem Analysis

### 1. PHANTOM EVENT SUBSCRIPTION (Critical)

**Problem:**
```python
# Line 48 in snapshot_publisher.py
EventType.ANIMATION_PARAMETER_CHANGED,
```

**Reality Check:**
- `EventType.ANIMATION_PARAMETER_CHANGED` exists in the enum (types.py:20)
- **NO EVENT CLASS EXISTS** for this type
- **NEVER PUBLISHED** anywhere in the codebase (grep confirms zero publishers)
- This is a dead event type that should have been removed

**Why This Exists:**
Looking at the codebase history:
1. `AnimationParameterChangedEvent` was defined in legacy `models/events.py` (line 34)
2. Event was **exported** for backward compatibility (line 34, 55)
3. But the actual event class **doesn't exist** in the new modular structure
4. Only `ZoneAnimationParamChangedEvent` exists and is actively used

**Impact:**
- Handler will **NEVER BE CALLED** for this event type
- Creates confusion about which events are actually active
- Suggests incomplete migration from old event system

---

### 2. DUCK TYPING ANTI-PATTERN (Critical)

**Current Implementation:**
```python
async def _on_zone_changed(self, event) -> None:  # Line 53 - NO TYPE HINT!
    zone_id: ZoneID | None = getattr(event, "zone_id", None)
    if not zone_id:
        return
```

**Why This is Dangerous:**

#### Type System Defeat
```python
event: Any  # Type checker sees this as "anything goes"
```
- **Mypy/Pylance cannot validate**: Handler could receive any object
- **No IDE autocomplete**: Developer gets no help
- **No refactoring safety**: Renaming `zone_id` attribute won't catch this usage
- **Runtime-only validation**: Errors only discovered when code runs

#### Maintenance Nightmare
If an event changes from having `zone_id` to `target_zone`:
```python
# With duck typing (BAD):
getattr(event, "zone_id", None)  # Silently returns None, hard to debug

# With isinstance (GOOD):
if isinstance(event, ZoneStaticStateChangedEvent):
    event.zone_id  # Mypy error: attribute doesn't exist → caught at type-check time
```

#### Semantic Confusion
The handler processes 4+ different event types with different meanings:
1. `ZONE_STATIC_STATE_CHANGED` - Color/brightness changed
2. `ZONE_RENDER_MODE_CHANGED` - Switched between static/animation
3. `ZONE_ANIMATION_CHANGED` - Different animation selected
4. `ZONE_ANIMATION_PARAM_CHANGED` - Animation parameter tweaked

These have **completely different payloads**:
- `ZoneStaticStateChangedEvent`: `zone_id`, `color`, `brightness`, `is_on`
- `ZoneRenderModeChangedEvent`: `zone_id`, `old`, `new`
- `ZoneAnimationChangedEvent`: `zone_id`, `animation_id`, `params`
- `ZoneAnimationParamChangedEvent`: `zone_id`, `param_id`, `value`

**But duck typing treats them all the same** because they share `zone_id`.

---

### 3. TYPE SAFETY VIOLATIONS (Critical)

**Violation 1: Missing Type Hints**
```python
async def _on_zone_changed(self, event) -> None:  # 'event' has NO type!
```

**Should Be (Option A - Union):**
```python
from typing import Union

ZoneEvent = Union[
    ZoneStaticStateChangedEvent,
    ZoneRenderModeChangedEvent,
    ZoneAnimationChangedEvent,
    ZoneAnimationParamChangedEvent,
]

async def _on_zone_changed(self, event: ZoneEvent) -> None:
```

**Or Better (Option B - Separate Handlers):**
```python
async def _on_static_changed(self, event: ZoneStaticStateChangedEvent) -> None:
async def _on_render_mode_changed(self, event: ZoneRenderModeChangedEvent) -> None:
async def _on_animation_changed(self, event: ZoneAnimationChangedEvent) -> None:
async def _on_param_changed(self, event: ZoneAnimationParamChangedEvent) -> None:
```

**Violation 2: Import Mismatch**
```python
# models/events.py exports:
from models.events import AnimationParameterChangedEvent  # This doesn't exist as a class!

# The ACTUAL event is:
from models.events.zone_runtime_events import ZoneAnimationParamChangedEvent
```

---

### 4. CODE STYLE VIOLATIONS

Per `.claude/CLAUDE.md` coding standards:

#### Violation: Type-Explicit APIs (Rule #3)
```python
# WRONG (current):
zone_id: ZoneID | None = getattr(event, "zone_id", None)
if not zone_id:
    return

# CORRECT (should be):
if isinstance(event, ZoneStaticStateChangedEvent):
    await self._handle_static_change(event)
elif isinstance(event, ZoneRenderModeChangedEvent):
    await self._handle_render_mode_change(event)
# ...
```

#### Violation: Type Hints (Rule #4)
```python
# WRONG:
async def _on_zone_changed(self, event) -> None:

# CORRECT:
async def _on_zone_changed(self, event: ZoneEvent) -> None:
```

---

## Architectural Issues

### Issue 1: Single Handler for Multiple Event Types

**Current:**
```python
def _subscribe(self) -> None:
    for event_type in (
        EventType.ZONE_STATIC_STATE_CHANGED,
        EventType.ZONE_RENDER_MODE_CHANGED,
        EventType.ZONE_ANIMATION_CHANGED,
        EventType.ZONE_ANIMATION_PARAM_CHANGED,
        EventType.ANIMATION_PARAMETER_CHANGED,  # ← PHANTOM!
    ):
        self.event_bus.subscribe(event_type, self._on_zone_changed)
```

**Problems:**
1. **Loss of Type Information**: EventBus dispatches typed events, but handler receives `Any`
2. **No Event-Specific Logic**: All events treated identically despite different semantics
3. **Performance**: Unnecessary `getattr()` calls on every event
4. **Debugging Difficulty**: Can't set breakpoint for specific event type

**Best Practice:**
```python
# Option A: Separate handlers (RECOMMENDED for different event types)
self.event_bus.subscribe(EventType.ZONE_STATIC_STATE_CHANGED, self._on_static_changed)
self.event_bus.subscribe(EventType.ZONE_RENDER_MODE_CHANGED, self._on_render_mode_changed)

# Option B: Type dispatch in handler (acceptable if logic is similar)
async def _on_zone_changed(self, event: ZoneEvent) -> None:
    if isinstance(event, ZoneStaticStateChangedEvent):
        await self._handle_static(event)
    elif isinstance(event, ZoneRenderModeChangedEvent):
        await self._handle_render_mode(event)
```

---

### Issue 2: Missing Validation

**Current:**
```python
zone_id: ZoneID | None = getattr(event, "zone_id", None)
if not zone_id:
    return  # Silent failure, no logging
```

**Problems:**
1. **Silent Failures**: Event without `zone_id` is ignored
2. **No Logging**: Impossible to debug why snapshots aren't updating
3. **Type Assumption**: Assumes `zone_id` is optional when it's actually required

**Should Be:**
```python
# With proper typing, this is IMPOSSIBLE:
async def _on_static_changed(self, event: ZoneStaticStateChangedEvent) -> None:
    # event.zone_id is guaranteed to exist by type system
    zone = self.zone_service.get_zone(event.zone_id)
    if not zone:
        log.warning(f"Snapshot for missing zone: {event.zone_id}")
        return
```

---

## Refactoring Solution

### Phase 1: Remove Phantom Event (IMMEDIATE)

**Changes:**
1. Remove `EventType.ANIMATION_PARAMETER_CHANGED` from subscription list
2. Verify no other code subscribes to this phantom event
3. Consider deprecating the enum value (or document as unused)

**Rationale:**
- Dead code that never fires
- Creates confusion
- Quick fix with zero risk

---

### Phase 2: Add Proper Type Hints (HIGH PRIORITY)

**Approach A: Union Type + Type Narrowing**
```python
from typing import Union
from models.events import (
    ZoneStaticStateChangedEvent,
    ZoneRenderModeChangedEvent,
    ZoneAnimationChangedEvent,
    ZoneAnimationParamChangedEvent,
)

ZoneEvent = Union[
    ZoneStaticStateChangedEvent,
    ZoneRenderModeChangedEvent,
    ZoneAnimationChangedEvent,
    ZoneAnimationParamChangedEvent,
]

async def _on_zone_changed(self, event: ZoneEvent) -> None:
    """Handle any zone-related change and emit fresh snapshot."""
    # Type narrowing via isinstance
    if isinstance(event, ZoneStaticStateChangedEvent):
        zone_id = event.zone_id
    elif isinstance(event, ZoneRenderModeChangedEvent):
        zone_id = event.zone_id
    # ... etc

    # Common logic
    zone = self.zone_service.get_zone(zone_id)
    if not zone:
        log.warning(f"Snapshot for missing zone: {zone_id}")
        return

    await self._publish_snapshot(zone_id)
```

**Pros:**
- Minimal code changes
- Preserves single-handler pattern
- Type checker validates all paths
- IDE autocomplete works

**Cons:**
- Still verbose type narrowing
- All events must have `zone_id` attribute

---

**Approach B: Protocol (RECOMMENDED)**
```python
from typing import Protocol

class HasZoneID(Protocol):
    """Protocol for events that have a zone_id attribute."""
    zone_id: ZoneID

async def _on_zone_changed(self, event: HasZoneID) -> None:
    """Handle any zone-related change and emit fresh snapshot."""
    zone = self.zone_service.get_zone(event.zone_id)
    if not zone:
        log.warning(f"Snapshot for missing zone: {event.zone_id}")
        return

    await self._publish_snapshot(event.zone_id)
```

**Pros:**
- Clean, minimal code
- Type-safe without boilerplate
- Works with any event that has `zone_id`
- **BEST FOR THIS USE CASE** - all events share the interface

**Cons:**
- Requires Python 3.8+ (already met)
- Less explicit about which events are supported

---

**Approach C: Separate Handlers**
```python
def _subscribe(self) -> None:
    self.event_bus.subscribe(
        EventType.ZONE_STATIC_STATE_CHANGED,
        self._on_static_changed
    )
    self.event_bus.subscribe(
        EventType.ZONE_RENDER_MODE_CHANGED,
        self._on_render_mode_changed
    )
    self.event_bus.subscribe(
        EventType.ZONE_ANIMATION_CHANGED,
        self._on_animation_changed
    )
    self.event_bus.subscribe(
        EventType.ZONE_ANIMATION_PARAM_CHANGED,
        self._on_param_changed
    )

async def _on_static_changed(self, event: ZoneStaticStateChangedEvent) -> None:
    await self._publish_snapshot(event.zone_id)

async def _on_render_mode_changed(self, event: ZoneRenderModeChangedEvent) -> None:
    await self._publish_snapshot(event.zone_id)

async def _on_animation_changed(self, event: ZoneAnimationChangedEvent) -> None:
    await self._publish_snapshot(event.zone_id)

async def _on_param_changed(self, event: ZoneAnimationParamChangedEvent) -> None:
    await self._publish_snapshot(event.zone_id)

async def _publish_snapshot(self, zone_id: ZoneID) -> None:
    """Common snapshot publishing logic."""
    zone = self.zone_service.get_zone(zone_id)
    if not zone:
        log.warning(f"Snapshot for missing zone: {zone_id}")
        return

    snapshot = ZoneSnapshotDTO.from_zone(zone)
    await self.event_bus.publish(
        ZoneSnapshotUpdatedEvent(zone_id=zone_id, snapshot=snapshot)
    )
```

**Pros:**
- Maximum type safety
- Event-specific logic easy to add
- Explicit, clear intent
- Best for future extensibility

**Cons:**
- More code initially
- Duplicate calls to `_publish_snapshot`

---

### Phase 3: Enhanced Logging & Error Handling

**Current Issues:**
- Silent failures when `zone_id` missing
- No logging when zone doesn't exist
- No metrics/monitoring

**Improvements:**
```python
async def _on_zone_changed(self, event: HasZoneID) -> None:
    """Handle zone change and emit snapshot."""
    zone = self.zone_service.get_zone(event.zone_id)
    if not zone:
        log.warning(
            "Snapshot requested for missing zone",
            zone_id=event.zone_id.name,
            event_type=event.type.name,
        )
        return

    try:
        snapshot = ZoneSnapshotDTO.from_zone(zone)
        await self.event_bus.publish(
            ZoneSnapshotUpdatedEvent(zone_id=event.zone_id, snapshot=snapshot)
        )
        log.debug(
            "Published zone snapshot",
            zone=event.zone_id.name,
            event_type=event.type.name,
        )
    except Exception as e:
        log.error(
            "Failed to publish zone snapshot",
            zone_id=event.zone_id.name,
            error=str(e),
            exc_info=True,
        )
```

---

## Recommended Solution: Protocol Approach

After analyzing all options, **Protocol (Approach B)** is optimal because:

1. **Minimal Changes**: Single handler pattern preserved
2. **Maximum Type Safety**: Type checker validates `zone_id` access
3. **Clean Code**: No verbose type narrowing or duplicate handlers
4. **Future-Proof**: Any new event with `zone_id` automatically works
5. **Performance**: No runtime overhead vs duck typing

---

## Complete Refactored Implementation

```python
from __future__ import annotations

from typing import Protocol
from api.socketio.zones.dto import ZoneSnapshotDTO
from services.zone_service import ZoneService
from services.event_bus import EventBus
from models.events.types import EventType
from models.events.zone_snapshot_events import ZoneSnapshotUpdatedEvent
from models.enums import ZoneID
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SNAPSHOT)


class HasZoneID(Protocol):
    """
    Protocol for events that contain a zone_id attribute.

    This allows type-safe handling of multiple event types that share
    the zone_id interface without duck typing or verbose Union types.
    """
    zone_id: ZoneID


class SnapshotPublisher:
    """
    Publishes UI-facing ZoneSnapshotUpdatedEvent in response to
    domain-level zone/animation events.

    Responsibilities:
    - Listen to zone-related domain events
    - Build ZoneSnapshot from current ZoneService state
    - Publish snapshot event for frontend/websocket layer

    Architecture:
    - Uses Protocol for type-safe multi-event handling
    - All subscribed events must have 'zone_id: ZoneID' attribute
    - Translates granular domain events → coarse UI snapshots
    """

    def __init__(
        self,
        *,
        zone_service: ZoneService,
        event_bus: EventBus,
    ):
        self.zone_service = zone_service
        self.event_bus = event_bus
        self._subscribe()
        log.info("SnapshotPublisher initialized")

    # ------------------------------------------------------------------
    # Event Subscriptions
    # ------------------------------------------------------------------

    def _subscribe(self) -> None:
        """
        Subscribe to all zone-related events that require snapshot updates.

        Note: ANIMATION_PARAMETER_CHANGED removed (phantom event, never published).
        Actual event is ZONE_ANIMATION_PARAM_CHANGED.
        """
        event_types = (
            EventType.ZONE_STATIC_STATE_CHANGED,      # Color/brightness/on-off
            EventType.ZONE_RENDER_MODE_CHANGED,       # Static ↔ Animation switch
            EventType.ZONE_ANIMATION_CHANGED,         # New animation selected
            EventType.ZONE_ANIMATION_PARAM_CHANGED,   # Animation parameter changed
        )

        for event_type in event_types:
            self.event_bus.subscribe(event_type, self._on_zone_changed)
            log.debug(f"Subscribed to {event_type.name}")

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    async def _on_zone_changed(self, event: HasZoneID) -> None:
        """
        Handle any zone-related change and emit fresh snapshot.

        Uses Protocol typing (HasZoneID) for type-safe handling of multiple
        event types without duck typing or verbose isinstance checks.

        Args:
            event: Any event with a zone_id attribute (ZoneStaticStateChangedEvent,
                   ZoneRenderModeChangedEvent, ZoneAnimationChangedEvent, etc.)
        """
        # Validate zone exists
        zone = self.zone_service.get_zone(event.zone_id)
        if not zone:
            log.warning(
                "Snapshot requested for missing zone",
                zone_id=event.zone_id.name,
                event_type=getattr(event, 'type', 'Unknown').name,
            )
            return

        # Build and publish snapshot
        try:
            snapshot = ZoneSnapshotDTO.from_zone(zone)

            await self.event_bus.publish(
                ZoneSnapshotUpdatedEvent(
                    zone_id=event.zone_id,
                    snapshot=snapshot,
                )
            )

            log.debug(
                "Published zone snapshot",
                zone=event.zone_id.name,
                event_type=getattr(event, 'type', 'Unknown').name,
            )

        except Exception as e:
            log.error(
                "Failed to publish zone snapshot",
                zone_id=event.zone_id.name,
                error=str(e),
                exc_info=True,
            )
```

---

## Alternative: Separate Handlers Implementation

For teams that prefer explicit handler separation:

```python
from __future__ import annotations

from api.socketio.zones.dto import ZoneSnapshotDTO
from services.zone_service import ZoneService
from services.event_bus import EventBus
from models.events.types import EventType
from models.events import (
    ZoneStaticStateChangedEvent,
    ZoneRenderModeChangedEvent,
    ZoneAnimationChangedEvent,
    ZoneAnimationParamChangedEvent,
)
from models.events.zone_snapshot_events import ZoneSnapshotUpdatedEvent
from models.enums import ZoneID
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SNAPSHOT)


class SnapshotPublisher:
    """
    Publishes UI-facing ZoneSnapshotUpdatedEvent in response to
    domain-level zone/animation events.

    Architecture: Separate typed handlers for each event type.
    """

    def __init__(
        self,
        *,
        zone_service: ZoneService,
        event_bus: EventBus,
    ):
        self.zone_service = zone_service
        self.event_bus = event_bus
        self._subscribe()
        log.info("SnapshotPublisher initialized")

    # ------------------------------------------------------------------
    # Event Subscriptions
    # ------------------------------------------------------------------

    def _subscribe(self) -> None:
        """Subscribe to zone-related events with typed handlers."""
        self.event_bus.subscribe(
            EventType.ZONE_STATIC_STATE_CHANGED,
            self._on_static_state_changed,
        )
        self.event_bus.subscribe(
            EventType.ZONE_RENDER_MODE_CHANGED,
            self._on_render_mode_changed,
        )
        self.event_bus.subscribe(
            EventType.ZONE_ANIMATION_CHANGED,
            self._on_animation_changed,
        )
        self.event_bus.subscribe(
            EventType.ZONE_ANIMATION_PARAM_CHANGED,
            self._on_animation_param_changed,
        )

        log.debug("Subscribed to 4 zone event types")

    # ------------------------------------------------------------------
    # Typed Event Handlers
    # ------------------------------------------------------------------

    async def _on_static_state_changed(
        self,
        event: ZoneStaticStateChangedEvent
    ) -> None:
        """Handle static state change (color/brightness/on-off)."""
        await self._publish_snapshot(event.zone_id, "STATIC_STATE")

    async def _on_render_mode_changed(
        self,
        event: ZoneRenderModeChangedEvent
    ) -> None:
        """Handle render mode change (static ↔ animation)."""
        await self._publish_snapshot(event.zone_id, "RENDER_MODE")

    async def _on_animation_changed(
        self,
        event: ZoneAnimationChangedEvent
    ) -> None:
        """Handle animation change (new animation selected)."""
        await self._publish_snapshot(event.zone_id, "ANIMATION")

    async def _on_animation_param_changed(
        self,
        event: ZoneAnimationParamChangedEvent
    ) -> None:
        """Handle animation parameter change."""
        await self._publish_snapshot(event.zone_id, "ANIMATION_PARAM")

    # ------------------------------------------------------------------
    # Snapshot Publishing
    # ------------------------------------------------------------------

    async def _publish_snapshot(
        self,
        zone_id: ZoneID,
        change_type: str
    ) -> None:
        """
        Common snapshot publishing logic.

        Args:
            zone_id: Zone to snapshot
            change_type: Human-readable description for logging
        """
        zone = self.zone_service.get_zone(zone_id)
        if not zone:
            log.warning(
                "Snapshot requested for missing zone",
                zone_id=zone_id.name,
                change_type=change_type,
            )
            return

        try:
            snapshot = ZoneSnapshotDTO.from_zone(zone)

            await self.event_bus.publish(
                ZoneSnapshotUpdatedEvent(
                    zone_id=zone_id,
                    snapshot=snapshot,
                )
            )

            log.debug(
                "Published zone snapshot",
                zone=zone_id.name,
                change_type=change_type,
            )

        except Exception as e:
            log.error(
                "Failed to publish zone snapshot",
                zone_id=zone_id.name,
                change_type=change_type,
                error=str(e),
                exc_info=True,
            )
```

---

## Migration Strategy

### Step 1: Backward Compatibility Check
```bash
# Verify no other code publishes ANIMATION_PARAMETER_CHANGED
rg "EventType\.ANIMATION_PARAMETER_CHANGED" --type py
rg "publish.*ANIMATION_PARAMETER_CHANGED" --type py
```

**Expected Result:** Only `snapshot_publisher.py` and `types.py` reference it.

---

### Step 2: Implementation (Choose One Approach)

**Option A: Protocol Approach (RECOMMENDED)**
- Replace handler signature with `event: HasZoneID`
- Add Protocol definition
- Remove phantom event from subscription
- Add enhanced logging

**Option B: Separate Handlers**
- Create 4 typed handlers
- Extract `_publish_snapshot` common logic
- Remove phantom event
- Add enhanced logging

---

### Step 3: Testing

**Unit Tests:**
```python
# test_snapshot_publisher.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from models.events import ZoneStaticStateChangedEvent
from models.enums import ZoneID
from services.snapshot_publisher import SnapshotPublisher

@pytest.fixture
def mock_services():
    zone_service = MagicMock()
    event_bus = MagicMock()
    return zone_service, event_bus

async def test_static_state_changed_publishes_snapshot(mock_services):
    zone_service, event_bus = mock_services
    publisher = SnapshotPublisher(
        zone_service=zone_service,
        event_bus=event_bus,
    )

    # Create event
    event = ZoneStaticStateChangedEvent(
        zone_id=ZoneID.MAIN,
        color=Color(255, 0, 0),
    )

    # Mock zone
    mock_zone = MagicMock()
    zone_service.get_zone.return_value = mock_zone

    # Handle event
    await publisher._on_zone_changed(event)  # Or _on_static_state_changed

    # Verify snapshot published
    assert event_bus.publish.called
    published_event = event_bus.publish.call_args[0][0]
    assert published_event.zone_id == ZoneID.MAIN

async def test_missing_zone_logs_warning(mock_services, caplog):
    zone_service, event_bus = mock_services
    publisher = SnapshotPublisher(
        zone_service=zone_service,
        event_bus=event_bus,
    )

    event = ZoneStaticStateChangedEvent(zone_id=ZoneID.MAIN)
    zone_service.get_zone.return_value = None  # Zone missing

    await publisher._on_zone_changed(event)

    # Verify warning logged
    assert "missing zone" in caplog.text.lower()
    # Verify no publish attempt
    assert not event_bus.publish.called
```

**Integration Tests:**
```python
async def test_full_snapshot_flow(real_services):
    """Test actual event flow from zone change → snapshot publication."""
    zone_service = real_services.zone_service
    event_bus = real_services.event_bus

    # Set up subscriber
    snapshot_events = []
    async def capture_snapshot(event):
        snapshot_events.append(event)

    event_bus.subscribe(EventType.ZONE_SNAPSHOT_UPDATED, capture_snapshot)

    # Create publisher
    publisher = SnapshotPublisher(
        zone_service=zone_service,
        event_bus=event_bus,
    )

    # Trigger zone change
    await zone_service.set_static_color(ZoneID.MAIN, Color(255, 0, 0))

    # Wait for async propagation
    await asyncio.sleep(0.1)

    # Verify snapshot published
    assert len(snapshot_events) == 1
    assert snapshot_events[0].zone_id == ZoneID.MAIN
    assert snapshot_events[0].snapshot.color == Color(255, 0, 0)
```

---

### Step 4: Rollout

1. **Deploy refactored code** (no breaking changes to external interfaces)
2. **Monitor logs** for warnings about missing zones
3. **Verify WebSocket updates** still work for frontend
4. **Check type checker** passes (mypy/pylance)

---

### Step 5: Cleanup (Future)

**Consider deprecating unused event type:**
```python
# models/events/types.py
class EventType(Enum):
    # ...
    ANIMATION_PARAMETER_CHANGED = auto()  # DEPRECATED: Never published, use ZONE_ANIMATION_PARAM_CHANGED
```

Or remove entirely if migration is complete.

---

## Impact Analysis

### Files Modified
1. `src/services/snapshot_publisher.py` - Main refactoring
2. (Optional) `src/models/events/types.py` - Deprecation comment

### Files NOT Modified
- Event Bus: No changes to subscription/publish API
- Event definitions: All events unchanged
- SocketIO handler: Continues consuming `ZONE_SNAPSHOT_UPDATED`
- Controllers: No awareness of snapshot publisher internals

### Risk Assessment

**LOW RISK:**
- No breaking API changes
- Backward compatible event subscriptions
- Only internal implementation changes
- Enhanced type safety catches bugs earlier

---

## Comparison: Before vs After

### Before (Duck Typing)
```python
async def _on_zone_changed(self, event) -> None:  # event: Any
    zone_id = getattr(event, 'zone_id', None)    # Runtime check
    if not zone_id:                               # Silent failure
        return
```

**Problems:**
- No type hints
- Runtime-only validation
- Silent failures
- No IDE support
- Phantom event subscription

---

### After (Protocol)
```python
async def _on_zone_changed(self, event: HasZoneID) -> None:  # Type-safe
    zone = self.zone_service.get_zone(event.zone_id)         # Compile-time check
    if not zone:
        log.warning("Missing zone", zone_id=event.zone_id.name)  # Logged failure
        return
```

**Benefits:**
- Full type hints
- Compile-time validation
- Logged failures
- IDE autocomplete
- Phantom event removed

---

## Recommendations

### For This Codebase: **Protocol Approach**

**Rationale:**
1. **Simplicity**: Minimal code changes, single handler preserved
2. **Type Safety**: Full type checking without boilerplate
3. **Consistency**: Matches "all events need same treatment" semantic
4. **Pythonic**: Leverages Protocol (PEP 544) for structural typing
5. **Future-Proof**: New events with `zone_id` automatically work

### Alternative (Separate Handlers) If:
- Event-specific logic needed in future (e.g., different snapshot formats)
- Team prefers explicit over implicit typing
- Maximum type safety desired (no Protocol learning curve)

---

## Type System Deep Dive: Why Protocols?

### Traditional Approaches

**Approach 1: Union Types**
```python
ZoneEvent = Union[
    ZoneStaticStateChangedEvent,
    ZoneRenderModeChangedEvent,
    ZoneAnimationChangedEvent,
    ZoneAnimationParamChangedEvent,
]

async def _on_zone_changed(self, event: ZoneEvent) -> None:
    # Problem: Must use isinstance to access zone_id
    if isinstance(event, ZoneStaticStateChangedEvent):
        zone_id = event.zone_id
    elif isinstance(event, ZoneRenderModeChangedEvent):
        zone_id = event.zone_id
    # ... repetitive!
```

**Drawbacks:**
- Verbose type narrowing required
- Must update Union when new events added
- Still requires runtime checks

---

**Approach 2: Duck Typing (Current)**
```python
async def _on_zone_changed(self, event: Any) -> None:
    zone_id = getattr(event, 'zone_id', None)  # Unsafe!
```

**Drawbacks:**
- No type safety
- No IDE support
- Runtime-only errors

---

**Approach 3: Protocol (RECOMMENDED)**
```python
from typing import Protocol

class HasZoneID(Protocol):
    zone_id: ZoneID

async def _on_zone_changed(self, event: HasZoneID) -> None:
    zone_id = event.zone_id  # Type-safe! No isinstance needed.
```

**Advantages:**
- **Structural Typing**: Any class with `zone_id: ZoneID` matches
- **No Boilerplate**: Events don't need to inherit from base class
- **Type Safe**: `event.zone_id` validated at type-check time
- **IDE Support**: Full autocomplete and refactoring
- **Compile-Time Checks**: Mypy/Pylance catch errors before runtime

### Protocol in Action

```python
# All these events satisfy HasZoneID Protocol:
ZoneStaticStateChangedEvent(zone_id=ZoneID.MAIN, ...)    # ✓ Has zone_id
ZoneRenderModeChangedEvent(zone_id=ZoneID.MAIN, ...)     # ✓ Has zone_id
ZoneAnimationChangedEvent(zone_id=ZoneID.MAIN, ...)      # ✓ Has zone_id

# Type checker validates:
async def _on_zone_changed(self, event: HasZoneID) -> None:
    print(event.zone_id)        # ✓ Type-safe
    print(event.color)          # ✗ Error: HasZoneID doesn't define 'color'
    print(event.animation_id)   # ✗ Error: HasZoneID doesn't define 'animation_id'
```

This is **structural typing** - the protocol defines the interface, not inheritance.

---

## Final Recommendation: PROTOCOL APPROACH

### Implementation Priority
1. **Phase 1** (Immediate): Remove phantom event
2. **Phase 2** (High): Add Protocol type hint
3. **Phase 3** (Medium): Enhanced logging
4. **Phase 4** (Low): Consider event type deprecation

### Code to Deploy (Complete)
See "Complete Refactored Implementation" section above.

### Success Criteria
- ✓ Type checker passes (mypy --strict)
- ✓ All existing tests pass
- ✓ WebSocket updates still work
- ✓ Logs show enhanced error messages
- ✓ IDE autocomplete works for `event.zone_id`

---

## Appendix: EventBus Contract Verification

**Verify EventBus supports typed handlers:**
```python
# Check EventBus.subscribe signature
def subscribe(
    self,
    event_type: EventType,
    handler: Callable[[Event], Awaitable[None]]
) -> None:
```

**If EventBus expects `Event` base class:**
```python
# Protocol must inherit from Event
class HasZoneID(Event, Protocol):  # Combine inheritance + protocol
    zone_id: ZoneID
```

**Check models/events/base.py for Event base class structure.**

---

## Questions for Team

1. **Preference**: Protocol or Separate Handlers approach?
2. **Testing**: Add unit tests in this PR or separate?
3. **Deprecation**: Remove `ANIMATION_PARAMETER_CHANGED` enum now or document as deprecated?
4. **Logging Level**: Keep `debug` or upgrade to `info` for snapshot publishing?

---

## Summary

**Current State:**
- Duck typing defeats type system
- Phantom event never published
- Silent failures on missing zones
- No IDE support

**Proposed State:**
- Type-safe Protocol or separate handlers
- Phantom event removed
- Logged failures with context
- Full IDE support and type checking

**Effort:** 2-3 hours
**Risk:** Low (backward compatible)
**Impact:** High (maintainability, type safety, debuggability)
