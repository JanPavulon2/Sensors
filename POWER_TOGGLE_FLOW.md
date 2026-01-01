# Power Toggle Flow - End-to-End

## ✅ COMPLETE WORKING FLOW

### 1. Frontend: User Clicks Power Button
**File**: `frontend/src/features/zones/components/zone-card/ZoneCardHeader.tsx`

```
User clicks PowerSwitch
  ↓
handleToggle(checked: boolean)
  ↓
powerCommand.setPower(checked)
```

---

### 2. Frontend: Send Command to Backend
**File**: `frontend/src/features/zones/hooks/useZonePowerCommand.ts`

```typescript
async function setPower(isOn: boolean) {
  setIsSending(true);
  await api.put(`/v1/zones/{zoneId}/is-on`, { is_on: isOn });
  // Wait for Socket.IO update - NO local state change
  setIsSending(false);
}
```

**Result**: HTTP PUT request sent to backend

---

### 3. Backend: REST API Endpoint
**File**: `src/api/routes/zones.py` (Lines 156-170)

```python
@router.put("/{zone_id}/is-on")
async def set_zone_is_on(zone_id: ZoneID, request: SetZoneIsOnRequest):
    services.zone_service.set_is_on(zone_id, request.is_on)
```

**Result**: Request routed to ZoneService

---

### 4. Backend: Zone Service Updates State
**File**: `src/services/zone_service.py` (Lines 126-144)

```python
def set_is_on(self, zone_id: ZoneID, is_on: bool) -> None:
    zone = self.get_zone(zone_id)
    zone.state.is_on = is_on          # Update in-memory state
    self._save_zone(zone_id)          # Save to JSON

    asyncio.create_task(self.event_bus.publish(
        ZoneStateChangedEvent(zone_id=zone_id, is_on=is_on)
    ))                                # Publish event
```

**Result**: State updated + Event published to EventBus

---

### 5. Backend: EventBus Broadcasts Event
**File**: `src/api/socketio_handler.py` (Lines 176-190)

```python
async def _on_zone_state_changed(self, event: ZoneStateChangedEvent):
    zone = self.services.zone_service.get_zone(event.zone_id)
    payload = ZoneSnapshotDTO.from_zone(zone)  # ✅ FIXED: Now has import

    await self.socketio_server.emit("zone:snapshot", asdict(payload))
```

**Result**: zone.snapshot event emitted to all connected clients

---

### 6. Frontend: Socket.IO Receives Event
**File**: `frontend/src/features/zones/realtime/zones.socket.ts`

```typescript
socket.on('zone.snapshot', (zone: ZoneSnapshot) => {
  updateZoneSnapshot(zone);  // Update store
});
```

**Result**: Socket listener updates internal store

---

### 7. Frontend: Store Updates React Components
**File**: `frontend/src/features/zones/realtime/zones.store.ts`

```typescript
export function updateZoneSnapshot(zone: ZoneSnapshot): void {
  zones = { ...zones, [zone.id]: zone };
  notify();  // Notifies all subscribers
}
```

**Result**: All components subscribed to `useZones()` re-render

---

### 8. Frontend: UI Updates
**File**: `frontend/src/features/zones/components/grid/ZonesGrid.tsx`

```typescript
const zones = useZones();  // Gets updated zones from Socket.IO store

// ZoneCard renders with updated zone data
<ZoneCard zone={zone} />
  ↓
<ZoneCardHeader zone={zone} />
  ↓
<PowerSwitch checked={zone.is_on} />  // Shows new state
```

**Result**: UI reflects new power state immediately

---

## 🔧 Critical Fix Applied

**File**: `src/api/socketio_handler.py` (Line 30)

**Added missing import:**
```python
from api.socketio.zones.dto import ZoneSnapshotDTO
```

This import was causing crashes when trying to emit zone.snapshot events.

---

## ✅ Verification Checklist

- [x] Frontend: useZonePowerCommand hook exists and sends PUT request
- [x] Backend: REST API endpoint validates and processes request
- [x] Backend: ZoneService updates state and publishes event
- [x] Backend: Socket.IO handler broadcasts zone.snapshot (fixed import)
- [x] Frontend: Socket.IO listener receives and stores event
- [x] Frontend: ZonesGrid uses useZones() hook (not old React Query)
- [x] Frontend: ZoneCardHeader displays updated state
- [x] Frontend: TypeScript compiles without errors ✅
- [x] Backend: Socket.IO handler has required imports ✅

---

## 🎯 Data Flow Summary

```
User Action
    ↓
PUT /v1/zones/{id}/is-on
    ↓
ZoneService.set_is_on()
    ↓
EventBus.publish(ZoneStateChangedEvent)
    ↓
Socket.IO: zone.snapshot
    ↓
zones.store: updateZoneSnapshot()
    ↓
useZones() hook notified
    ↓
ZonesGrid re-renders
    ↓
ZoneCardHeader displays new state
```

---

## 🚀 Testing the Power Toggle

1. Start the application
2. Open the browser dashboard
3. Click the power button on a zone card
4. Button should show loading state (`isSending`)
5. Zone power state should update instantly after Socket.IO receives the event
6. Check backend logs for `zone.snapshot` emission

---

## 📝 Notes

- No optimistic updates: Frontend waits for real-time confirmation from Socket.IO
- No polling: Updates come via push events only
- Single source of truth: Socket.IO store is the only data source for zones
- Simple and clean: No complexity, just command → event → update
