# Work Tasks & Tracker

This file maintains the current task list for the Diuna project. Tasks are tracked by priority (1-5, where 1 is highest) and status.

## Active Tasks

1. **Priority 1** - Make application review and write down requirements for version v0.5  
   Status: NOT-STARTED  
   Description: Conduct a thorough review of the Diuna application, identify bugs and todos, specify requirements for v0.5 completion, and plan next development phases/milestones.  
   **Sub-tasks:**  
   - Review current features and architecture  
   - Identify bugs and outstanding todos  
   - Define v0.5 requirements (what must be done to call it complete)  
   - Plan next phases and milestones

---

## v0.5 Bugs & Todos (NOW)

### Priority 1 - Critical Bugs

2. **Frontend app hangs when changing length param**  
   Status: COMPLETED  
   Issue: Param value is overriding and saving even if it's the same value, causing hang  
   Target: v0.5  
   **Fix implemented:**
   - Frontend: Added 300ms debounce to range slider + optimistic local state
   - Slider responsive (follows cursor), animation updates in real-time, no artificial jumping
   - Backend: Added value-change check in `set_animation_param` to skip save if unchanged

3. **Snake animation renders wrong length**  
   Status: COMPLETED  
   Issue: Snake anim has length 5 but renders 1–2 LEDs. After changing to length 6 it renders correctly  
   Target: v0.5  
   **Fix implemented:**
   - Fixed loop range: `range(-1, length + 1)` → `range(-1, length)` (was iterating one too many)
   - Fixed SNAKE PARAMS default: 1 → 5 (matched frontend and step() method)
   - Applied same fix to COLOR_SNAKE animation

4. **Logs tab doesn't load historical data before Debug page visit**  
   Status: COMPLETED  
   Issue: When opening logs tab, old logs not shown until event triggers new entry. Historical logs should preload  
   Target: v0.5  
   **Fix implemented:**
   - Added check for pre-existing socket connection: if socket already connected on mount, request history immediately
   - Previously only requested history on 'connect' event, which doesn't fire if socket was already connected
   - Frontend now loads 500 previous logs regardless of when hook initializes

### Priority 2 - Important Fixes

5. **Breathe animation shows 5000% intensity on frontend**  
   Status: COMPLETED  
   Issue: Initial intensity display is incorrect  
   Target: v0.5  
   **Fix implemented:**
   - Root cause: State.json had intensity as 0-100 (old scale), backend uses 0.0-1.0
   - Frontend was assuming 0.0-1.0 and multiplying by 100, causing 5000%
   - Added scale detection: if value > 1, treat as already 0-100; otherwise convert 0.0-1.0 → 0-100

6. **Hue color picker is small and pixelated**  
   Status: COMPLETED  
   Issue: Color hue circle should expand to fill space and look good (see screenshot)  
   Target: v0.5  
   **Fix implemented:**
   - Made canvas responsive: uses container width/height up to max constraints
   - Added device pixel ratio support for crisp rendering on high-DPI displays
   - Uses ResizeObserver to adapt to container size changes
   - Maintains minimum size (140px compact, 240px full)

7. **Tasks tab on Debug page sometimes empty**  
   Status: COMPLETED  
   Issue: Tab shows empty list when navigating to Debug page because task data is only requested on socket connect (and socket is already connected)  
   Target: v0.5  
   **Fix implemented:**
   - Updated `useTaskWebSocket` to request task stats + task list immediately when the socket is already connected on mount (and store is initially empty)


8. **Change app name to Aurora Lighting**  
   Status: NOT-STARTED  
   Issue: Branding update across frontend and backend  
   Target: v0.5

9. **Add new "Zones" page to navigation**  
   Status: COMPLETED  
   Issue: Create dedicated page for zone management, second in menu after Dashboard  
   Target: v0.5  
   **Implementation:**
   - Created `/frontend/src/pages/Zones.tsx` with ZonesGrid component
   - Added route `/zones` in App.tsx routing
   - Updated MainLayout navigation to include "Zones" as second menu item with Grid3X3 icon
   - Page shows only zones view (no frame visualizer, info cards, or add animation button)

---

## Future Features (FUTURE)

9. **Tree view in logs with collapsible nodes**  
   Status: NOT-STARTED  
   Priority: 4  
   Target: Post-v0.5

## Completed

(Completed tasks moved here for reference)

---

## Priority Guide
- **1**: Critical blocker, start immediately
- **2**: High priority, finish today/this week  
- **3**: Medium priority, schedule soon
- **4**: Nice-to-have, lower urgency
- **5**: Backlog, no current timeline

## Status Legend
- `NOT-STARTED`: Task not begun
- `IN-PROGRESS`: Currently working
- `BLOCKED`: Waiting on blocker
- `COMPLETED`: Done
