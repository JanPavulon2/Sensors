# API Issues & Action Items

**Created:** 2025-12-28
**Related Files:**
- `.claude/context/api-endpoints-map.md` - Complete endpoint reference
- `.claude/context/refactoring-summary-routes.md` - Refactoring details

---

## Critical Issues

### 🔴 Issue 1: Animation Parameters Path Mismatch (CRITICAL)

**Severity:** HIGH - Causes 404 errors

**Problem:**
- Backend endpoint: `/api/v1/zones/{zone_id}/animation/parameters`
- Frontend calls: `/api/v1/zones/{zone_id}/animation-parameters`
- Result: Animation parameter updates fail with 404

**Affected Files:**
- Backend: `src/api/routes/zones.py` (line 432)
- Frontend: `frontend/src/features/zones/api/queries.ts` (line ~256)

**Fix:**
Update frontend to match backend path:
```typescript
// Before (WRONG)
const response = await api.put(`/v1/zones/${zoneId}/animation-parameters`, data);

// After (CORRECT)
const response = await api.put(`/v1/zones/${zoneId}/animation/parameters`, data);
```

**Testing:**
1. Update animation parameters in UI
2. Verify no 404 errors
3. Check animation parameters actually change

---

## High Priority Issues

### 🟠 Issue 2: Old Animation Endpoints Still in system.py

**Severity:** MEDIUM - Code duplication

**Problem:**
- Animation endpoints moved to `animations.py`
- Old endpoints in `system.py` removed
- Frontend still calls `/system/animations` (old path)

**Status:** Partially fixed (endpoints removed, but frontend paths need update)

**Affected Files:**
- Frontend: `frontend/src/features/animations/api/queries.ts`

**Fix:**
Update frontend to use new path:
```typescript
// Before (old path)
const response = await api.get('/v1/system/animations');

// After (new path)
const response = await api.get('/v1/animations');
```

**Note:** Both paths work during transition; new path is cleaner and more RESTful

---

### 🟠 Issue 3: Unused System Status Endpoint

**Severity:** MEDIUM - Dead code

**Problem:**
- Frontend has hook `useSystemStatusQuery()` that calls `GET /system/status`
- Backend endpoint NOT implemented
- Hook will fail if called

**Affected Files:**
- Frontend: `frontend/src/shared/hooks/useSystem.ts`
- Backend: `src/api/routes/system.py` (missing endpoint)

**Options:**
1. **Implement endpoint** (prefer if needed):
   ```python
   @router.get("/status", response_model=SystemStatusResponse)
   async def get_system_status(services = Depends(get_service_container)):
       # Return system status (fps, memory, uptime, etc.)
   ```

2. **Remove unused hook** (if not needed):
   - Delete `useSystemStatusQuery()`
   - Check for any usage
   - Update imports

**Recommendation:** Implement `GET /system/status` for completeness

---

## Medium Priority Issues

### 🟡 Issue 4: Animation Stop Endpoint Not Used

**Severity:** LOW - Works but indirect

**Problem:**
- Backend has: `POST /zones/{zone_id}/animation/stop`
- Frontend doesn't call it directly
- Instead, uses `PUT /zones/{zone_id}/render-mode` with STATIC mode
- Works, but inconsistent pattern

**Affected Files:**
- Backend: `src/api/routes/zones.py` (line 400)
- Frontend: `frontend/src/features/zones/api/queries.ts`

**Current Flow:**
```typescript
// To stop animation, frontend calls:
await api.put(`/v1/zones/${zoneId}/render-mode`, { render_mode: 'STATIC' });

// Instead of:
// await api.post(`/v1/zones/${zoneId}/animation/stop`);
```

**Options:**
1. **Promote `/animation/stop`:** Make it primary endpoint
   - More explicit
   - Cleaner semantics
   - Requires frontend update

2. **Deprecate `/animation/stop`:** Remove endpoint
   - Simpler codebase
   - render-mode is already multi-purpose
   - Less confusing

**Recommendation:** Deprecate `/animation/stop` in favor of render-mode (already working)

---

### 🟡 Issue 5: Task Endpoints Not Used by Frontend

**Severity:** LOW - Available but unused

**Problem:**
- Backend has task monitoring endpoints
- Frontend doesn't use them
- Available for future use or debugging

**Endpoints:**
- `GET /system/tasks/summary`
- `GET /system/tasks` (all)
- `GET /system/tasks/active`
- `GET /system/tasks/failed`

**Note:** These are useful for debugging, keep as-is

---

## Low Priority (Nice to Have)

### 💡 Enhancement 1: Standardize Response Format

**Current State:** Most endpoints return data at root level

**Suggestion:** Consider envelope pattern for consistency:
```json
{
  "status": "success",
  "data": { /* actual response */ },
  "error": null,
  "timestamp": "2025-12-28T00:00:00Z"
}
```

**Note:** This is a larger change; evaluate if worth doing

---

### 💡 Enhancement 2: Animation Parameter Type Definitions

**Current State:** Animation parameters are strings

**Suggestion:** Define parameter types and validation
```python
# In animations.yaml
parameters:
  - name: "ANIM_INTENSITY"
    type: "range"
    min: 0
    max: 100
    default: 50
```

**Benefit:** Frontend can validate before sending, better UX

---

### 💡 Enhancement 3: Pagination for Task Endpoints

**Current State:** All tasks returned in single response

**Suggestion:** Add pagination for large task lists
```python
@router.get("/tasks", params=[limit, offset])
async def get_all_tasks(limit: int = 100, offset: int = 0):
    # Return paginated results
```

---

## Action Items Summary

### Immediate (Fix ASAP)
- [ ] **Fix animation parameters path** (Issue #1)
  - Priority: CRITICAL
  - Effort: 2 minutes
  - Impact: Unblocks animation parameter updates

### Short Term (This Sprint)
- [ ] Update animation endpoint paths in frontend (Issue #2)
  - Priority: HIGH
  - Effort: 5 minutes
  - Impact: Cleaner API usage

- [ ] Implement or remove system status endpoint (Issue #3)
  - Priority: MEDIUM
  - Effort: 10-30 minutes
  - Impact: Completes API implementation

- [ ] Document animation stop endpoint decision (Issue #4)
  - Priority: MEDIUM
  - Effort: 5 minutes
  - Impact: Clarity for future developers

### Later (Nice to Have)
- [ ] Response format standardization (Enhancement #1)
- [ ] Animation parameter types (Enhancement #2)
- [ ] Task endpoint pagination (Enhancement #3)

---

## Testing Checklist

### Before Deploying
- [ ] All animation operations work (start, stop, parameters)
- [ ] Zone controls respond correctly
- [ ] WebSocket connections stay open
- [ ] No 404 errors in browser console
- [ ] Animation parameters actually update on devices

### After Deploying
- [ ] Monitor error logs for 404s
- [ ] Verify all endpoints in Swagger/docs
- [ ] Test animation transitions
- [ ] Check WebSocket reconnection

---

## Related Documentation

- **API Endpoints Map:** `.claude/context/api-endpoints-map.md`
- **Refactoring Summary:** `.claude/context/refactoring-summary-routes.md`
- **Route Files:**
  - `src/api/routes/animations.py` (NEW)
  - `src/api/routes/zones.py`
  - `src/api/routes/system.py`
  - `src/api/routes/logger.py`

---

## Decision Log

### Decision 1: Extract Animation Routes
**Date:** 2025-12-28
**Decision:** Create dedicated `animations.py` router for animation definitions
**Rationale:** Cleaner organization, better separation of concerns
**Status:** ✅ Implemented

### Decision 2: Keep Zone Animation Operations in zones.py
**Date:** 2025-12-28
**Decision:** Don't move zone-specific animation ops
**Rationale:** These are zone operations, not animation definitions
**Status:** ✅ Implemented

### Decision 3: Animation Parameters Path
**Status:** ⏳ PENDING - Need frontend fix
**Options:**
- Option A: Fix frontend path (RECOMMENDED) → `/animation/parameters`
- Option B: Change backend path → `/animation-parameters`
**Recommendation:** Option A (backend is correct, cleaner path structure)

---

## Statistics

| Metric | Value |
|--------|-------|
| Total Issues Found | 5 |
| Critical | 1 |
| High | 1 |
| Medium | 2 |
| Low | 1 |
| Enhancements | 3 |
| Estimated Fix Time | ~30 minutes |
| Estimated Impact | HIGH (fixes actual bugs) |

