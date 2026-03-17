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
   Status: IN-PROGRESS  
   Issue: Snake anim has length 5 but renders 1–2 LEDs. After changing to length 6 it renders correctly  
   Target: v0.5

4. **Logs tab doesn't load historical data before Debug page visit**  
   Status: NOT-STARTED  
   Issue: When opening logs tab, old logs not shown until event triggers new entry. Historical logs should preload  
   Target: v0.5

### Priority 2 - Important Fixes

5. **Breathe animation shows 5000% intensity on frontend**  
   Status: NOT-STARTED  
   Issue: Initial intensity display is incorrect  
   Target: v0.5

6. **Hue color picker is small and pixelated**  
   Status: NOT-STARTED  
   Issue: Color hue circle should expand to fill space and look good (see screenshot)  
   Target: v0.5

7. **Tasks tab on Debug page sometimes empty**  
   Status: NOT-STARTED  
   Issue: Tab with tasks not always populated, inconsistent data fetch  
   Target: v0.5

8. **Change app name to Aurora Lighting**  
   Status: NOT-STARTED  
   Issue: Branding update across frontend and backend  
   Target: v0.5

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
