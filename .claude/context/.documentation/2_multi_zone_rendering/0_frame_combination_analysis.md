---
Last Updated: 2025-11-25
Updated By: Architecture Analysis
Changes: Initial comprehensive analysis of multi-zone frame combination and optimization
---

# Multi-Zone Frame Combination Architecture Analysis

## Executive Summary

The Diuna LED control system elegantly solves the challenge of rendering **multiple zones in different states simultaneously** (some static, some animating, some pulsing, some off) using a **priority-based frame queue system**.

**The key insight**: Rather than trying to merge zone states at render time, the system uses **priority queues to select the highest-priority complete frame**, and **animation frames pre-merge static zones** before submission.

---

## 1. The Problem We're Solving

### Scenario: Complex Multi-Zone States

Imagine this setup:

```
FLOOR zone:    Running SNAKE animation (updates every frame)
LAMP zone:     Static WHITE color (user set it, doesn't change)
LEFT zone:     OFF (disabled by user)
RIGHT zone:    Pulsing CYAN (static mode with pulse enabled)
TOP zone:      Transitioning from RED → BLUE (animation changing to static)
```

**Naive Approach (DON'T DO THIS)**:
```python
# ❌ WRONG - Zone state is scattered everywhere
floor_animation.render_to_strip()         # Writes FLOOR pixels
lamp_controller.render_to_strip()         # Writes LAMP pixels
left_controller.render_to_strip()         # Writes LEFT pixels
right_controller.render_to_strip()        # Writes RIGHT pixels
transition_service.render_to_strip()      # Writes TOP pixels
strip.show()  # ← But which state wins if conflicts?
```

**Problems**:
- Multiple `show()` calls → flicker
- Who decides priorities?
- Static zones get overwritten by animations
- Complexity explodes with N zones × M sources

### The Solution: Frame-Based Priority System

```
                 ┌─────────────────────────────────────────┐
                 │   Multiple Frame Sources                 │
                 │   (each submits complete frames)         │
                 └──────────┬──────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
   ANIMATION Sources                    STATIC Sources
   (Animations pre-merge               (Pulse, Manual static,
    static zones)                      Transitions)
        │                                       │
        ├─ PixelFrame (pri=30)                 ├─ ZoneFrame (pri=20-40)
        │  {FLOOR: [animated],                 │  {LAMP: white@75%,
        │   LAMP: [merged],                    │   RIGHT: cyan@90%}
        │   LEFT: [black]}                     │
        │                                      │
        └──────────────┬──────────────────────┘
                       │
          ┌────────────────────────────┐
          │  Priority Queue System     │
          │                            │
          │  Pri 50: DEBUG    []      │
          │  Pri 40: TRANSITION []   │
          │  Pri 30: ANIMATION [P]   │  ← Only ONE frame
          │  Pri 20: PULSE    []      │     per priority level
          │  Pri 10: MANUAL   []      │     is selected!
          └────────────────────────────┘
                       │
         ┌─────────────────────────────┐
         │ FrameManager._render_loop() │
         │ (60 FPS)                    │
         └────────────┬────────────────┘
                      │
        ┌─────────────────────────────┐
        │ SELECT FRAME                │
        │ Pick HIGHEST priority       │
        │ non-expired frame           │
        │ → PixelFrame (pri=30)       │
        └────────────┬────────────────┘
                     │
        ┌────────────────────────────┐
        │ RENDER TO HARDWARE         │
        │ (single DMA transfer)      │
        │ All zones update together  │
        └────────────────────────────┘
```

---

## 2. How Multiple Zones Are Combined

### Architecture: Two Approaches

#### Approach A: **Frame Merging in Source** (Current Implementation)

**AnimationEngine merges static zones BEFORE submitting**:

```python
# AnimationEngine._run_loop() - Line 493-509

# 1. Animation yields pixels for FLOOR only
zone_pixels_dict = {
    ZoneID.FLOOR: [Color.red(), Color.red(), Color.black(), ...]
}

# 2. Before submit, merge STATIC zones
for zone in self.zones:
    zone_id = zone.config.id

    # Skip if animated or OFF
    if zone_id in zone_pixels_dict:
        continue  # Already animated
    if zone.state.mode == ZoneRenderMode.OFF:
        continue  # OFF = black, defaults to black in frame

    # If STATIC, add its current color
    if zone.state.mode == ZoneRenderMode.STATIC:
        rgb = zone.get_rgb()
        zone_length = self.zone_lengths.get(zone_id, 0)
        zone_pixels_dict[zone_id] = [rgb] * zone_length  # ← Merge!
        log.debug(f"Merged static zone: {zone_id.name}")

# 3. Submit COMPLETE frame with merged zones
frame = PixelFrame(
    zone_pixels=zone_pixels_dict,  # {FLOOR: animated, LAMP: static, ...}
    priority=FramePriority.ANIMATION,
    source=FrameSource.ANIMATION,
    ttl=0.1
)
await self.frame_manager.submit_pixel_frame(frame)
```

**Advantages**:
- ✅ FrameManager is simple (just selects + renders)
- ✅ No zone state awareness needed in FrameManager
- ✅ Every animation frame is "complete" and independent
- ✅ Static zones don't need separate rendering passes

**Disadvantages**:
- ❌ AnimationEngine must know about zone states
- ❌ Extra work every frame to merge static zones
- ❌ If animation changes, must rebuild entire frame

---

#### Approach B: **Frame Merging in FrameManager** (Alternative)

```python
# THEORETICAL - Not implemented

class FrameManager:
    async def _select_and_merge_frame(self):
        """
        Select highest priority frame from any source,
        then merge with lower-priority frames if needed.
        """

        # Select highest priority
        selected = self._select_main_frame_by_priority()
        if not selected:
            selected = self._get_default_idle_frame()

        # If selected is ANIMATION (pri=30), merge PULSE (pri=20) and MANUAL (pri=10)
        if selected.priority.value == 30:
            # For each zone NOT in selected, check lower priorities
            for zone_id in self.zone_service.all_zones():
                if zone_id not in selected.zone_pixels:
                    # Try to find this zone in PULSE frames
                    pulse_frame = self.main_queues[20].get()
                    if pulse_frame and zone_id in pulse_frame.zone_colors:
                        # Add PULSE zone to selected frame
                        selected.zone_pixels[zone_id] = pulse_frame.zone_colors[zone_id]

        return selected
```

**Advantages**:
- ✅ Clean separation: animation only cares about animation
- ✅ Multiple sources don't need to coordinate
- ✅ Could support partial frame updates (not all zones in every frame)

**Disadvantages**:
- ❌ Complex merging logic in FrameManager
- ❌ FrameManager must know zone structure
- ❌ Coordination between priority levels
- ❌ Perf hit: examine multiple queue levels per frame

---

### Current Implementation Detail: Where Zone Merging Happens

**Three main zones-merging locations**:

#### 1. **AnimationEngine** (Most Important)
- Merges static zones into animation frames
- Location: `src/animations/engine.py:493-509`
- Frequency: Every animation frame (60 FPS during animation)

```python
# Before submitting animation frame:
for zone in self.zones:
    if zone.state.mode == ZoneRenderMode.STATIC:
        zone_pixels_dict[zone_id] = [color] * zone_length  # Merge
```

#### 2. **ZoneFrame Rendering**
- When selected frame is ZoneFrame (from PULSE/MANUAL/TRANSITION)
- Location: `src/engine/frame_manager.py:425-449`

```python
def _render_zone_frame(self, frame: ZoneFrame, strip: ZoneStrip):
    # Convert per-zone colors to full pixel buffer
    full_frame = strip.build_frame_from_zones(frame.zone_colors)

    # Render atomically (no per-zone flicker)
    strip.apply_pixel_frame(full_frame)
```

#### 3. **Priority Fallback** (Automatic)
- When high-priority frames expire, lower priorities take over
- Location: `src/engine/frame_manager.py:318-338`

```python
for priority_value in sorted(self.main_queues.keys(), reverse=True):
    queue = self.main_queues[priority_value]
    while queue:
        frame = queue.popleft()
        if not frame.is_expired():
            return frame  # ← Only valid frame
```

---

## 3. Frame Rendering Frequency: Do We Always Run at 60 FPS?

### Short Answer: **YES, FrameManager always runs at 60 FPS**

```python
async def _render_loop(self) -> None:
    """Main render loop @ target FPS."""
    frame_delay = 1.0 / self.fps  # 16.67ms @ 60 FPS

    while self.running:
        # Select frame
        main_frame = await self._select_main_frame_by_priority()
        preview_frame = await self._select_preview_frame_by_priority()

        # Render if any frame available
        if main_frame or preview_frame:
            self._render_atomic(main_frame, preview_frame)
            self.frames_rendered += 1

        # Wait for next frame time
        await asyncio.sleep(frame_delay)
```

**Location**: `src/engine/frame_manager.py:278-315`

### What This Means for Power Consumption

**Scenario**: All zones are STATIC (no animation, no pulse)

```
Timeline (60 FPS = 16.67ms per frame):

Frame 0:    Select MANUAL frame (pri=10) → Render → LED DMA (2.7ms)
                                              ↓
                                        Hardware latches pixels
                                              ↓
                                        Sleep 13.97ms
            ↑
Frame 1:    [Wake from sleep]
            Select MANUAL frame (SAME as Frame 0, not expired)
                ↓
            Render SAME pixels AGAIN → LED DMA (2.7ms)
                                              ↓
                                        Hardware latches SAME pixels
                                              ↓
                                        Sleep 13.97ms

Frame 2:    [Same as Frame 1]
Frame 3:    [Same as Frame 1]
...
Frame 60:   [Same as Frame 1]
```

**Result**: The **same pixel data** is sent to hardware **60 times per second**, even though the data hasn't changed!

---

## 4. How Frame Expiration Prevents Stale Renders

### TTL (Time-To-Live) System

Each frame has a TTL that determines how long it's valid:

```python
@dataclass
class BaseFrame:
    priority: FramePriority
    source: FrameSource
    timestamp: float = field(default_factory=time.time)
    ttl: float = 0.1  # Default: 100ms

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl
```

**Location**: `src/models/frame.py:18-28`

### TTL Values by Source

| Source | Priority | TTL | Expiration After |
|--------|----------|-----|------------------|
| **Animation** | 30 | 0.1s | 6 frames @ 60 FPS |
| **Pulse** | 20 | 0.1s | 6 frames @ 60 FPS |
| **Transition** | 40 | 0.1s | 6 frames @ 60 FPS |
| **Static (Manual)** | 10 | 1.5s | 90 frames @ 60 FPS |
| **Debug** | 50 | 5.0s | 300 frames @ 60 FPS |

### Scenario: Animation Stops → Falls Back to Static

```
Timeline (60 FPS):

Frame 0-100:     AnimationEngine submits ANIMATION frames (pri=30, ttl=0.1s)
                 FrameManager selects pri=30 → Render animation

Frame 101:       AnimationEngine stops (user changes mode)
                 No new ANIMATION frames submitted
                 Last ANIMATION frame: timestamp=Frame 100 + 5ms

Frame 105:       ANIMATION frame EXPIRED (100ms passed)
                 _select_main_frame_by_priority() skips it
                 Looks at pri=40 (TRANSITION) → none available
                 Looks at pri=20 (PULSE) → NONE (pulse task isn't running)
                 Looks at pri=10 (MANUAL) → FOUND! (ttl=1.5s, still valid)
                 ↓
                 Render MANUAL frame (static zone colors)

Frame 106-196:   Continue rendering MANUAL frames (static colors persist)

Frame 197:       MANUAL frame EXPIRES (1500ms passed)
                 No valid frames in any queue
                 _render_atomic() receives None
                 → Renders nothing (LEDs remain at last valid state)
```

---

## 5. How Static Zones Are Protected from Animation Overrides

### Dual Protection Mechanism

#### Protection 1: **Merging** (Primary)

AnimationEngine merges static zone colors into animation frames **before submission**:

```python
# Animation engine's perspective:
#
# Generate pixels for animated zones only:
zone_pixels_dict = {ZoneID.FLOOR: [...]}  # Only FLOOR animated

# Before submit, add static zones:
zone_pixels_dict[ZoneID.LAMP] = [Color.white(), ...]  # Add LAMP static
zone_pixels_dict[ZoneID.RIGHT] = [Color.cyan(), ...]  # Add RIGHT static

# Submit complete frame:
frame = PixelFrame(zone_pixels=zone_pixels_dict)
```

**Result**: FrameManager receives COMPLETE frame with all zones:

```python
{
    FLOOR: [red, red, black, ...],    # Animated
    LAMP: [white, white, white],      # Static (merged)
    RIGHT: [cyan, cyan, cyan],        # Static (merged)
    LEFT: [black, black, black]       # OFF (merged)
}
```

**Important**: The LAMP and RIGHT colors in this frame are **captured at submission time**. If the user changes LAMP brightness, the next animation frame will have the new LAMP color merged in.

#### Protection 2: **Priority Fallback** (Backup)

If animation stops, static frames (PULSE/MANUAL priority) take over:

```
Animation running:        ANIMATION pri=30 visible
                         ↓
Animation stops:         ANIMATION frames expire (after 100ms)
                         ↓
FrameManager selects:    pri=40? No → pri=30? Expired → pri=20 (PULSE)
                         ↓
PULSE frames visible:    Static zone with pulse effect
                         ↓
User disables pulse:     PULSE frames stop coming
                         ↓
FrameManager selects:    pri=20? Expired → pri=10 (MANUAL)
                         ↓
MANUAL frames visible:   Pure static color (no pulse)
```

---

## 6. Partial Updates and Optimization

### Current System: NO Partial Updates

**The FrameManager ALWAYS renders the ENTIRE strip**, even if only one zone changed:

```python
def _render_zone_frame(self, frame: ZoneFrame, strip: ZoneStrip):
    # Frame contains SOME zones:
    frame.zone_colors = {ZoneID.LAMP: Color.white()}  # Only LAMP!

    # But we build FULL pixel frame for ALL zones:
    full_frame = strip.build_frame_from_zones(frame.zone_colors)
    #                                         ↑
    #                        Missing zones default to black!

    # And render entire strip:
    strip.apply_pixel_frame(full_frame)  # Send ALL 90 pixels to hardware
```

**Behavior**:

```
Frame 1: Submit ZoneFrame(LAMP=white)
         → build_frame_from_zones() adds LAMP white
         → Missing zones (FLOOR, LEFT, RIGHT) → default to black
         → Render 90 pixels to hardware (entire strip, even though only LAMP changed)

Frame 2: Submit ZoneFrame(LAMP=white, RIGHT=cyan)
         → build_frame_from_zones() adds LAMP white + RIGHT cyan
         → Missing zones → black
         → Render 90 pixels to hardware (entire strip)
```

### Optimization: Why This is Acceptable

#### 1. **Zone States Are Maintained by Frame Sources**

Static mode controller maintains LAMP brightness:

```python
# StaticModeController doesn't submit partial updates
# It submits ALL zones it controls:

def adjust_param(self, delta: int):
    # Get ALL zone colors (not just the changed one)
    zones_colors = {}
    for zone_id in zone_service.all_zones():
        if is_selected(zone_id):
            zones_colors[zone_id] = (color, brightness)
        else:
            # Also include non-selected zones! (preserve their state)
            zones_colors[zone_id] = (zone.state.color, zone.state.brightness)

    # Submit complete frame
    self.strip_controller.submit_all_zones_frame(zones_colors)
```

#### 2. **Animation Merges Static Zones**

Animation frames already include static zone colors:

```python
# Animation engine handles merging:
for zone in self.zones:
    if zone.state.mode == ZoneRenderMode.STATIC:
        zone_pixels_dict[zone_id] = [color] * length  # Include static
```

#### 3. **Hardware Timing is Limiting Factor**

The bottleneck is **hardware DMA transfer time**, not CPU processing:

```
WS2811 Protocol Timing:
- 90 pixels × 24 bits × 1.25µs = 2.7ms per frame
- Reset time: 50µs
- Minimum frame time: 2.75ms

Theoretical max FPS: 1000ms / 2.75ms = 364 FPS

Current: 60 FPS = 16.67ms per frame
Hardware busy: 2.75ms
Idle time: 13.92ms (83% idle!)
```

Sending 90 pixels or 50 pixels takes similar time because the bottleneck is the serial WS2811 protocol, not the CPU.

---

## 7. What Happens When All Zones Are Static (No Animation)

### Frame Submission Pattern

```
Frame 0:     User sets LAMP to white
             StaticModeController.submit_all_zones_frame()
                 └─> FrameManager.submit_zone_frame(ZoneFrame, pri=MANUAL, ttl=1.5s)
                 └─> Appended to main_queues[10]

Frame 1-90:  No new frames submitted (static content unchanged)
             FrameManager._select_main_frame_by_priority() still finds
             the SAME ZoneFrame from Frame 0 (TTL not expired yet)

             Renders to hardware: SAME pixels again

Frame 91:    [Same as Frame 1-90]
...
Frame 150:   User adjusts LAMP brightness
             StaticModeController.submit_all_zones_frame()
                 └─> NEW ZoneFrame submitted
                 └─> Old frame in queue evicted (maxlen=2)

             FrameManager now renders NEW frame

Frame 151+:  New frame renders until expired or replaced
```

### Rendering Frequency During Static-Only Operation

**YES, FrameManager runs at full 60 FPS**, but:

```
Rendering: 60 times per second
Frame changes: Only when user interacts (encoder, button press)
Hardware updates: 60 times per second (same pixels every time)
```

### Power Optimization Opportunity

**Currently not optimized**, but could be:

```python
# CURRENT (no optimization):
if main_frame or preview_frame:
    self._render_atomic(main_frame, preview_frame)  # Sends to hardware every frame

# OPTIMIZED (theoretical):
if main_frame != self.last_rendered_frame:
    self._render_atomic(main_frame, preview_frame)  # Only if different
    self.last_rendered_frame = main_frame
else:
    # Skip hardware update (pixels already set correctly)
    pass

await asyncio.sleep(frame_delay)
```

**Benefit**: Reduce GPIO/DMA overhead by ~95% during static-only operation.

---

## 8. Complete State Transition Examples

### Example 1: User Starts Animation While LAMP is Static

**Initial State**:
```
FLOOR: STATIC mode, color=black
LAMP:  STATIC mode, color=white, brightness=100%
LEFT:  OFF mode
```

**Events**:

```
T=0ms:   User selects ANIMATION mode for FLOOR

T=5ms:   AnimationEngine starts
         Frame 0: Yields FLOOR animation pixels
         Merge static zones:
           FLOOR: [animated pixels] (from animation engine)
           LAMP: [white, white, white, ...] (merged static)
           LEFT: [black] (OFF mode, not in dict)
         Submit PixelFrame(pri=ANIMATION, ttl=0.1s)

T=21ms:  FrameManager._render_loop() Frame 1
         _select_main_frame_by_priority():
           Pri 50? Empty
           Pri 40? Empty
           Pri 30? Found! (ANIMATION frame from T=5ms, not expired)
         Render ANIMATION frame → Hardware

T=37ms:  Frame 2: AnimationEngine yields more pixels
         Merge: FLOOR animated + LAMP white + LEFT black
         Submit PixelFrame
         Render to hardware

         [Continues at 60 FPS]

T=1000ms: User changes LAMP brightness to 75%
          StaticModeController.submit_all_zones_frame()
            └─> ZoneFrame(LAMP=white@75%, pri=MANUAL, ttl=1.5s)

          But AnimationEngine is still running!
          Next ANIMATION frame merge: LAMP white@75% now used

T=1017ms: FrameManager renders ANIMATION frame
          But now LAMP is at 75% brightness (merged from zone state)
          ANIMATION priority=30 > MANUAL priority=10
          → ANIMATION frame wins, but includes updated LAMP brightness

T=5000ms: User stops animation
          No new ANIMATION frames submitted
          Last ANIMATION frame from T=4995ms: timestamp=T=4995ms

T=5105ms: Frame N: Last ANIMATION frame EXPIRED
          _select_main_frame_by_priority():
            Pri 30? Expired (100ms passed)
            Pri 20? Empty (no pulse active)
            Pri 10? Found! (MANUAL frame with LAMP@75%)
          Render MANUAL frame → Hardware

          FLOOR shows black (not in MANUAL frame)
          LAMP shows white@75% (in MANUAL frame)
          LEFT shows black (OFF)
```

**Key Insight**: User's brightness change to LAMP immediately affects animation rendering, even though static and animation frames are separate.

---

### Example 2: Multiple Zones with Different Updates

**Setup**:
```
FLOOR: ANIMATION (Snake)
LAMP:  STATIC + PULSE
LEFT:  STATIC (no pulse)
RIGHT: OFF
```

**Frame Submissions**:

```
T=100ms:  AnimationEngine submits PixelFrame:
          {FLOOR: [animated], LAMP: [white], LEFT: [red]}
          pri=30, ttl=0.1s

T=120ms:  StaticModeController pulse task submits ZoneFrame:
          {LAMP: [white@80%]}
          pri=20, ttl=0.1s

T=140ms:  User adjusts LEFT brightness to 75%
          StaticModeController submits ZoneFrame:
          {LEFT: [red@75%]}
          pri=10, ttl=1.5s

T=157ms:  FrameManager selects frame:
          Pri 30? Found! (ANIMATION, submitted T=100ms, not expired)
          → Render ANIMATION frame

          But wait... LEFT is in both ANIMATION and MANUAL frames!
          ANIMATION wins (higher priority)
          → LEFT shows animation color (which merged the static value)

T=200ms:  (57ms after last ANIMATION submit)
          FrameManager selects:
          Pri 30? Found! (still valid, ttl=0.1s)
          → Render ANIMATION

T=210ms:  (60ms after ANIMATION, 90ms after PULSE)
          Both ANIMATION and PULSE are still valid
          Pri 30? Found! → Render ANIMATION

T=212ms:  (61ms after ANIMATION, 92ms after PULSE)
          ANIMATION frame EXPIRED
          PULSE frame still valid
          Pri 30? Expired
          Pri 20? Found! (PULSE) → Render PULSE frame

          LAMP shows white@80% (from PULSE)
          FLOOR shows black (PULSE doesn't have it)
          LEFT shows red@75% (PULSE doesn't have it, goes black)

          ⚠️ PROBLEM: LEFT turned black because PULSE frame
             doesn't include it, and ANIMATION frame expired!
```

**Analysis**: When ANIMATION frame expires, PULSE takes over, but PULSE only updates LAMP (not FLOOR/LEFT). This could cause unexpected visual changes.

---

## 9. Architecture Strengths vs Optimization Opportunities

### ✅ Current Strengths

| Strength | Why It Works |
|----------|-------------|
| **Priority arbitration** | Multiple sources can submit without coordination |
| **Automatic cleanup** | Expired frames discarded, memory bounded |
| **Frame merging** | Static zones preserved during animations |
| **Atomic rendering** | Single DMA = no flicker |
| **Fire-and-forget** | Non-blocking submission |
| **Fallback handling** | Auto-selection of lower priorities when high expire |

### ⚠️ Optimization Opportunities

#### 1. **Redundant Hardware Updates**

**Current**: Same pixels sent 60 times/sec even when static

```python
# Status @ Frame 0: Submit ZoneFrame(LAMP=white)
#         @ Frame 1-90: Render SAME pixels 90 times
#         (2.7ms × 90 = 243ms of unnecessary DMA)

# Optimization:
frame_hash = hash(frame.zone_colors)
if frame_hash != self.last_frame_hash:
    self._render_atomic(frame, preview_frame)
    self.last_frame_hash = frame_hash
```

**Benefit**: ~95% reduction in GPIO overhead during static-only mode

**Cost**: Minor CPU overhead for hashing, small memory for hash storage

---

#### 2. **Partial Frame Updates**

**Current**: When PULSE zone changes, entire strip sent

```python
# PULSE frame only has LAMP:
{LAMP: white@80%}

# But build_frame_from_zones() fills all zones:
{FLOOR: black, LAMP: white@80%, LEFT: black, RIGHT: black}
# ↑ Default to black if not in frame!

# Optimization: Support partial updates
# Some zones preserve previous pixel state
```

**Benefit**: No reset to black for zones not in frame

**Cost**: Tracking per-zone state, more complex rendering logic

---

#### 3. **TTL Customization per Animation**

**Current**: All animations use ttl=0.1s

```python
# Issue: Slow animations like Breathe (1-2s cycle)
# might expire between frames if system is busy

# Optimization: Per-animation TTL
class BaseAnimation:
    def __init__(self):
        self.frame_ttl = 0.1  # Default

    # Override in subclass:
    class BreatheAnimation:
        frame_ttl = 1.0  # Longer for slow animations
```

**Benefit**: Better handling of variable-speed animations

**Cost**: Per-animation configuration

---

#### 4. **Zone Masking in Frames**

**Current**: Frames either include zone or it defaults to black

```python
# Animation frame only has FLOOR:
{FLOOR: [animated]}

# Rendering defaults missing zones to black
# But LAMP was white! It turns black when animation switches

# Optimization: Zone mask in frame
class PixelFrame:
    zone_pixels: Dict[ZoneID, List[Color]]
    zone_mask: Set[ZoneID]  # Only update these zones

    # Zones not in mask preserve previous state
```

**Benefit**: Zones not explicitly controlled stay unchanged

**Cost**: More frame memory, complex rendering logic

---

#### 5. **Frame Deduplication in Queues**

**Current**: Identical frames may queue multiple times

```python
# Frame A submitted 3 times (all identical)
# Queue: [Frame A, Frame A, Frame A]
# Only first rendered, others discarded (maxlen=2)

# Optimization: Before queue.append(frame):
if frame != queue[-1]:
    queue.append(frame)  # Only add if different
```

**Benefit**: Cleaner queue management

**Cost**: Frame equality check (deep comparison expensive)

---

#### 6. **Priority Range per Source**

**Current**: Fixed priority per source (ANIMATION=30 always)

```python
# Could support variable priority:
# Fast animations (pri=30)
# Slow animations (pri=25)  ← Lower priority, static can override

# Example: User starts pulse while Breathe running
# Pulse pri=20 < Breathe pri=25
# → Pulse doesn't hide Breathe (intended behavior)
```

**Benefit**: Fine-grained control without priority conflicts

**Cost**: More complex priority system

---

## 10. Comparison: Current vs Optimal Architecture

### Current Implementation

```
┌─ Animation merges static zones
│  └─ PixelFrame(animated + static) submitted @ pri=30
│
├─ FrameManager selects highest priority (pri=30)
│
├─ Renders entire strip every frame (even if static)
│
└─ Static zones protected by merging
```

**Pros**:
- Simple, clean implementation
- Animation engine handles merging in one place
- Static zones never override animations

**Cons**:
- Redundant DMA transfers for static content
- Zone defaults to black if not in frame
- No partial updates

---

### Optimized Alternative

```
┌─ Animation yields only animated zones
│  └─ PixelFrame(animated only) @ pri=30
│
├─ Static controller submits zones separately
│  └─ ZoneFrame(static colors) @ pri=10
│
├─ FrameManager merges frames by zone
│  └─ For each zone: select highest priority value
│
├─ Conditional rendering (only if changed)
│  └─ Hash comparison before DMA
│
└─ Zone masking (zones not updated preserve state)
```

**Pros**:
- ~95% less DMA overhead during static mode
- Clean separation (animation ≠ static)
- Supports partial updates
- Zones preserve state if not in frame

**Cons**:
- More complex FrameManager logic
- Frame merging across priority levels
- Zone state awareness required

---

## 11. Recommendation: Hybrid Approach

**For Diuna**: Keep **Approach A (current)** because:

1. ✅ **Simplicity matters on Raspberry Pi**
   - Limited CPU
   - Real-time constraints
   - Simpler = fewer bugs

2. ✅ **Current performance is fine**
   - 60 FPS target achieved
   - Hardware is limiting factor (DMA timing)
   - CPU optimization yields minimal gains

3. ✅ **Merging in animation source is clean**
   - Single responsibility: animation generates frames
   - No scattered coordination logic

4. ✅ **Frame expiration handles most use cases**
   - Automatic fallback works well
   - Zone states maintained by sources

### If Optimization Needed Later:

**Phase 1** (Easy):
- Add frame hash comparison to skip redundant DMA
- Minimal code change, significant power reduction

**Phase 2** (Medium):
- Custom TTL per animation
- Zone masking in frames

**Phase 3** (Hard):
- FrameManager-level merging
- Partial zone updates

---

## Conclusion

The Diuna frame-based rendering system elegantly solves multi-zone rendering through:

1. **Priority queues** - Higher priority sources always win
2. **Frame merging** - Animation pre-merges static zones
3. **TTL expiration** - Automatic cleanup and fallback
4. **Atomic rendering** - Single DMA transfer prevents flicker

The system achieves smooth 60 FPS rendering while maintaining independent zone control. While the current implementation always updates hardware even for static content, the simplicity and robustness of the approach make it suitable for the Raspberry Pi environment.

**For 95% of use cases, the current approach is optimal. Optimization opportunities exist but have diminishing returns on limited hardware.**
