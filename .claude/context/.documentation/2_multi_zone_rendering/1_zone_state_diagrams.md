---
Last Updated: 2025-11-25
Updated By: Architecture Analysis
Changes: Visual diagrams and state machine representations
---

# Multi-Zone Rendering: Visual Diagrams and State Machines

## 1. Zone States and Their Rendering Sources

### Zone Render Modes

```
┌─────────────────────────────────────────────────────┐
│           ZONE STATE DIAGRAM                        │
└─────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │   CREATED    │
                    └───────┬──────┘
                            │
                    ┌───────▼──────────┐
                    │   POWER_OFF      │
                    │                  │
              ┌─────┴────┬──────────────┴─────┐
              │          │                    │
              ▼          ▼                    ▼
          ┌─────┐   ┌─────────┐       ┌──────────┐
          │ OFF │   │ STATIC  │       │ANIMATION │
          └─────┘   └────┬────┘       └──────────┘
              △          │                  △
              │          ▼                  │
              │   ┌──────────────┐          │
              │   │STATIC+PULSE  │          │
              │   │(brightness   │          │
              │   │ oscillates)  │          │
              │   └──────────────┘          │
              │                            │
              └────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Rendering Source per Zone Mode                      │
├─────────────────────────────────────────────────────┤
│ OFF            → Black (no frame needed)            │
│ STATIC         → ZoneFrame (MANUAL pri=10, ttl=1.5s)│
│ STATIC+PULSE   → ZoneFrame (PULSE pri=20, ttl=0.1s) │
│ ANIMATION      → PixelFrame (ANIMATION pri=30)      │
│                  (merged with other zones' states)   │
└─────────────────────────────────────────────────────┘
```

---

## 2. Complete Frame Rendering Pipeline

### Flow: From Zone State to LED Hardware

```
┌────────────────────────────────────────────────────────────────────┐
│                    ZONE STATE MANAGEMENT LAYER                     │
│                  (src/state/, src/services/)                       │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ FLOOR zone   │  │ LAMP zone    │  │ LEFT zone    │            │
│  │              │  │              │  │              │            │
│  │ mode: ANIM   │  │ mode: STATIC │  │ mode: OFF    │            │
│  │ color: ---   │  │ color: white │  │ color: black │            │
│  │ brightness:--│  │ brightness: 75%
  │ brightness:--│            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                   FRAME SOURCE LAYER                               │
│           (animations/, controllers/, services/)                   │
│                                                                    │
│  AnimationEngine                StaticModeController              │
│  ────────────────               ──────────────────                │
│  Yields FLOOR animation         Monitors zone states              │
│  pixels only:                                                      │
│                                 On brightness change:             │
│  {FLOOR: [red, red, ...]}       Collect ALL zones:               │
│                                                                    │
│  Before submit:                 {FLOOR: ?, LAMP: white@75%,      │
│  Merge static zones:            LEFT: black}                      │
│  + LAMP (static)                                                   │
│  + LEFT (black/OFF)             Submit ZoneFrame:                │
│                                 pri=PULSE (20)                    │
│  {FLOOR: [animated],            ttl=0.1s                          │
│   LAMP: [white, white...],                                        │
│   LEFT: [black, black...]}                                        │
│                                                                    │
│  Submit PixelFrame:                                               │
│  pri=ANIMATION (30)                                               │
│  ttl=0.1s                                                         │
└────────────────────────────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
          ┌──────────┐  ┌──────────┐  ┌──────────┐
          │Animation │  │   Pulse  │  │  Manual  │
          │Queue[30] │  │Queue[20] │  │Queue[10] │
          │          │  │          │  │          │
          │ [Frame]  │  │ [Frame]  │  │ [Frame]  │
          └──────────┘  └──────────┘  └──────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│              FRAME MANAGER SELECTION LAYER                         │
│           (src/engine/frame_manager.py)                            │
│                                                                    │
│  _select_main_frame_by_priority():                               │
│  ──────────────────────────────────                              │
│                                                                    │
│  For priority in [50, 40, 30, 20, 10]:                           │
│      For each frame in queue[priority]:                          │
│          if not frame.is_expired():                              │
│              return frame  ← SELECTED FRAME                      │
│                                                                    │
│  Result: pri=30 ANIMATION frame selected                         │
│          (pri=20 PULSE and pri=10 MANUAL ignored)                │
└────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│              FRAME RENDERING LAYER                                 │
│           (src/engine/frame_manager.py)                            │
│                                                                    │
│  _render_pixel_frame(PixelFrame):                                │
│  ─────────────────────────────────                              │
│                                                                    │
│  Convert PixelFrame zone_pixels to full pixel buffer:           │
│                                                                    │
│  zone_pixels = {                                                 │
│    FLOOR: [red, red, red, red, ...],         ← Zone 0 pixels    │
│    LAMP: [white, white, white],              ← Zone 1 pixels    │
│    LEFT: [black, black, ...]                 ← Zone 2 pixels    │
│  }                                                                │
│                                                                    │
│  full_pixel_buffer = [                       ← Flat list         │
│    red, red, red, red, ...,                  ← FLOOR pixels     │
│    white, white, white,                      ← LAMP pixels      │
│    black, black, ...                         ← LEFT pixels      │
│  ]                                                                │
│                                                                    │
│  Call: ZoneStrip.show_full_pixel_frame(zone_pixels)             │
└────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│              HARDWARE LAYER (ATOMIC)                               │
│           (src/zone_layer/zone_strip.py)                          │
│                                                                    │
│  apply_pixel_frame(pixel_frame: List[Color]):                   │
│  ──────────────────────────────────────────                     │
│                                                                    │
│  Convert Color objects to RGB tuples:                           │
│  [Color.red(), Color.white(), ...]                             │
│       ↓                                                           │
│  [(255,0,0), (255,255,255), ...]                               │
│       ↓                                                           │
│  Call WS281xStrip.apply_frame(rgb_list)                       │
│       ↓                                                           │
│  ┌─────────────────────────────────────────┐                    │
│  │ SINGLE DMA TRANSFER TO GPIO             │                    │
│  │ (all pixels updated atomically)         │                    │
│  │                                         │                    │
│  │ Timing: 2.7ms for 90 pixels            │                    │
│  └─────────────────────────────────────────┘                    │
│       ↓                                                           │
│  Hardware latches pixels                                         │
│       ↓                                                           │
│  ✓ FLOOR shows animated pixels                                  │
│  ✓ LAMP shows white color                                       │
│  ✓ LEFT shows black (OFF)                                       │
│  (All three zones update simultaneously - NO FLICKER)           │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Priority-Based Frame Selection Flowchart

### Frame Selection Algorithm

```
START
  │
  ▼
┌─────────────────────────────┐
│ FrameManager._render_loop() │
│ (60 FPS timer fired)        │
└──────────────┬──────────────┘
               │
               ▼
     ┌─────────────────────┐
     │ Time to render?     │
     │ (16.67ms passed)    │
     └────────┬────────────┘
              │ YES
              ▼
┌────────────────────────────────────────┐
│ _select_main_frame_by_priority()       │
│                                        │
│ priorities = [50, 40, 30, 20, 10]     │
│                                        │
│ For each priority (highest to lowest): │
│   queue = main_queues[priority]        │
│                                        │
│   ┌─────────────────────────────────┐ │
│   │ pri=50 (DEBUG)?                 │ │
│   │   queue empty? → try pri=40     │ │
│   │   frame.expired? → try pri=40   │ │
│   │   FOUND → RETURN ✓              │ │
│   └─────────────────────────────────┘ │
│                ▼                       │
│   ┌─────────────────────────────────┐ │
│   │ pri=40 (TRANSITION)?            │ │
│   │   queue empty? → try pri=30     │ │
│   │   frame.expired? → try pri=30   │ │
│   │   FOUND → RETURN ✓              │ │
│   └─────────────────────────────────┘ │
│                ▼                       │
│   ┌─────────────────────────────────┐ │
│   │ pri=30 (ANIMATION)?             │ │
│   │   queue empty? → try pri=20     │ │
│   │   frame.expired? → try pri=20   │ │
│   │   FOUND → RETURN ✓              │ │
│   └─────────────────────────────────┘ │
│                ▼                       │
│   ┌─────────────────────────────────┐ │
│   │ pri=20 (PULSE)?                 │ │
│   │   queue empty? → try pri=10     │ │
│   │   frame.expired? → try pri=10   │ │
│   │   FOUND → RETURN ✓              │ │
│   └─────────────────────────────────┘ │
│                ▼                       │
│   ┌─────────────────────────────────┐ │
│   │ pri=10 (MANUAL)?                │ │
│   │   queue empty? → return None    │ │
│   │   frame.expired? → return None  │ │
│   │   FOUND → RETURN ✓              │ │
│   └─────────────────────────────────┘ │
└────────────────────────────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
    ┌────────┐   ┌──────────┐
    │ Frame? │   │ No Frame?│
    └────┬───┘   └────┬─────┘
         │            │
         ▼            ▼
    Render      Skip rendering
    to HW       (LEDs stay as-is)
```

---

## 4. State Transition: Multiple Zones with Different Updates

### Timeline: Zones Changing States

```
TIME (ms)  FLOOR         LAMP          LEFT          RENDERING
─────────  ─────         ────          ────          ──────────

0          STATIC        STATIC        OFF
           (red)         (white)       (black)       → MANUAL frame [pri=10]
                                                       RED + WHITE + BLACK

100        Switch to     (unchanged)   (unchanged)
           ANIMATION                                 → ANIMATION frame [pri=30]
           (Snake)                                     ANIMATED + WHITE + BLACK

200        (animating)   Change to     (unchanged)
                         STATIC+PULSE                → ANIMATION frame [pri=30]
                         Pulse starts                 ANIMATED + WHITE@pulse + BLACK

300        (animating)   (pulsing)     Change to     → ANIMATION frame [pri=30]
                                       STATIC        ANIMATED + WHITE@pulse + BLACK
                                       (red)         (but now LEFT has red, merged)

400        (animating)   (pulsing)     (unchanged)   → ANIMATION frame [pri=30]
                                                      ANIMATED + WHITE@pulse + RED

500        (animating)   Stop pulse    (unchanged)
           (still)       PULSE off                   → ANIMATION frame [pri=30]
           Still         Change to     (unchanged)   ANIMATED + WHITE + RED
           ANIMATION     WHITE+STATIC                (PULSE frame gone, MANUAL updated)
           (Snake)

600        Stop          (unchanged)   (unchanged)
           animation                                 → ~107ms gap with no ANIMATION
           SWITCH TO                                   frames submitted
           STATIC

707        (expired)     (unchanged)   (unchanged)   → MANUAL frame [pri=10]
           ANIMATION                                 WHITE + RED + BLACK
           frames all                               (FLOOR goes black - animation stopped)
           expired

800        (black)       (unchanged)   (unchanged)   → MANUAL frame [pri=10]
                                                      BLACK + WHITE + RED
```

---

## 5. Frame Queue Dynamics: What's Actually In the Queues?

### Scenario: Animation Running with Static Zones

```
SITUATION: FLOOR animating (Snake), LAMP static, LEFT static

FRAME SOURCES SUBMITTING:
┌──────────────────────────────────────────────┐
│ AnimationEngine (every ~16.67ms)             │
├──────────────────────────────────────────────┤
│ PixelFrame {                                 │
│   FLOOR: [red, red, red, red, red, ...],   │
│   LAMP: [white, white, white],              │
│   LEFT: [red, red, red]                     │
│ }                                            │
│ priority = ANIMATION (30)                   │
│ ttl = 0.1s                                  │
│ timestamp = T_current                       │
└──────────────────────────────────────────────┘
         │
         └─ Every 16.67ms, submit new frame
            (with updated animation + merged zones)


FRAME MANAGER QUEUES:
┌────────────────────────────────────────────────────┐
│ main_queues[50] (DEBUG)                            │
│ Status: Empty                                      │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ main_queues[40] (TRANSITION)                       │
│ Status: Empty                                      │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ main_queues[30] (ANIMATION)                        │
│ ┌────────────────────────────────────────────────┐ │
│ │ Frame A (submitted 16.67ms ago)                │ │
│ │ {FLOOR: [...], LAMP: [...], LEFT: [...]}      │ │
│ │ timestamp: T-16.67ms                           │ │
│ │ is_expired()? NO (100ms - 16.67ms = 83ms OK)  │ │
│ │ Status: VALID                                  │ │
│ └────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────┐ │
│ │ Frame B (just submitted)                       │ │
│ │ {FLOOR: [...], LAMP: [...], LEFT: [...]}      │ │
│ │ timestamp: T                                    │ │
│ │ is_expired()? NO (100ms - 0ms = 0ms OK)       │ │
│ │ Status: VALID                                  │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
│ Note: maxlen=2, so only last 2 frames kept         │
│       Older frames evicted automatically           │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ main_queues[20] (PULSE)                            │
│ Status: Empty (no pulse running)                   │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ main_queues[10] (MANUAL)                           │
│ Status: Empty (static controller not updating)    │
└────────────────────────────────────────────────────┘


FRAME SELECTION @ T:
_select_main_frame_by_priority() iterates:
  pri=50? Empty → skip
  pri=40? Empty → skip
  pri=30? Has Frame B (submitted 0ms ago)
         timestamp=T, ttl=0.1s
         is_expired()? (T - T) > 0.1s? NO → ✓ SELECTED

RENDER Frame B to hardware


FRAME SELECTION @ T+16.67ms:
_select_main_frame_by_priority() iterates:
  pri=50? Empty → skip
  pri=40? Empty → skip
  pri=30? Has Frame B (submitted 16.67ms ago)
         timestamp=T, ttl=0.1s
         is_expired()? (T+16.67ms - T) > 0.1s? NO → ✓ SELECTED
         (Frame A was evicted when Frame B arrived, due to maxlen=2)

RENDER Frame B again to hardware

[... continues until animation stops ...]


FRAME SELECTION @ T+110ms (animation stopped):
AnimationEngine stops submitting
  pri=50? Empty → skip
  pri=40? Empty → skip
  pri=30? Has Frame B (submitted 110ms ago)
         timestamp=T, ttl=0.1s
         is_expired()? (T+110ms - T) > 0.1s? YES → ✗ EXPIRED
         ↑ This frame is dead!
  pri=20? Empty (no pulse) → skip
  pri=10? Has old MANUAL frame from earlier
         timestamp=T-1000ms, ttl=1.5s
         is_expired()? (T+110ms - (T-1000ms)) > 1.5s?
                     1110ms > 1500ms? NO → ✓ SELECTED

RENDER old MANUAL frame (zones go static again)
```

---

## 6. Frame Expiration Timeline

### What Happens When Animation Stops?

```
ANIMATION RUNNING:
┌─────────────────────────────────────────────┐
│ T=0ms:    AnimationEngine submits Frame_0   │
│           pri=ANIMATION(30), ttl=0.1s       │
│           timestamp=0                       │
│           queues[30] = [Frame_0]            │
│                                             │
│ T=16.67ms: Render selects Frame_0           │
│           is_expired()? (16.67-0)>100? NO   │
│           → RENDER Frame_0                  │
│           AnimationEngine submits Frame_1   │
│           queues[30] = [Frame_0, Frame_1]   │
│           maxlen=2, so Frame_0 evicted      │
│           queues[30] = [Frame_1]            │
│                                             │
│ T=33.33ms: AnimationEngine submits Frame_2  │
│           Frame_1 evicted                   │
│           queues[30] = [Frame_2]            │
│           timestamp=33.33                   │
│                                             │
│ ... (continues every 16.67ms) ...           │
└─────────────────────────────────────────────┘

ANIMATION STOPS @ T=500ms:
┌─────────────────────────────────────────────┐
│ T=500ms:  AnimationEngine stops             │
│           Last submitted: Frame_N           │
│           timestamp=500                     │
│           queues[30] = [Frame_N]            │
│                                             │
│ T=516.67ms: Render selects Frame_N          │
│            is_expired()? (516.67-500)>100? NO
│            → RENDER Frame_N                 │
│                                             │
│ T=533.33ms: No new Frame submitted!         │
│            Render selects Frame_N           │
│            is_expired()? (533.33-500)>100? NO
│            → RENDER Frame_N                 │
│                                             │
│ T=550ms:   Still Frame_N                    │
│            is_expired()? (550-500)>100? NO  │
│            → RENDER Frame_N                 │
│                                             │
│ T=600ms:   Still Frame_N                    │
│            is_expired()? (600-500)>100? YES │
│            ✗ FRAME EXPIRED!                 │
│            Frame_N removed from queue       │
│            queues[30] = []                  │
│            Fallback to pri=20? Empty        │
│            Fallback to pri=10? Has MANUAL   │
│            → RENDER MANUAL frame (static)   │
│                                             │
│ T=616.67ms: Still no ANIMATION frames       │
│            Continue rendering MANUAL        │
│            (static zones visible)           │
│                                             │
│ T=2000ms:  MANUAL frame expires (1.5s TTL) │
│            queues[10] = []                  │
│            No valid frames in any queue     │
│            → NO RENDER (LEDs hold last state)
└─────────────────────────────────────────────┘
```

---

## 7. Complex Scenario: Zone State Conflicts

### When Multiple Zones Update at Different Rates

```
┌──────────────────────────────────────────────────────────────┐
│ SCENARIO: FLOOR animating, LAMP pulsing, LEFT static        │
└──────────────────────────────────────────────────────────────┘

SOURCES:
┌─ AnimationEngine (FLOOR)      → PixelFrame @ pri=30, ttl=0.1s
│  Submits every 16.67ms
│
├─ PulseTask (LAMP)             → ZoneFrame @ pri=20, ttl=0.1s
│  Submits 40× per second (25ms interval)
│
└─ ManualStatic (LEFT)          → ZoneFrame @ pri=10, ttl=1.5s
   Submitted once when user sets it


FRAME SELECTION TIMELINE:

T=0ms:
┌─ ANIMATION pri=30: Frame_A(FLOOR+LAMP+LEFT merged)
├─ PULSE pri=20: Empty (pulse hasn't started)
└─ MANUAL pri=10: Frame_M(LEFT static)

→ SELECT pri=30 (highest) → RENDER Frame_A

T=16.67ms:
┌─ ANIMATION pri=30: Frame_B(submitted, Frame_A evicted)
├─ PULSE pri=20: Empty
└─ MANUAL pri=10: Frame_M

→ SELECT pri=30 → RENDER Frame_B

T=25ms:
Pulse task activates! First PULSE frame submitted
┌─ ANIMATION pri=30: Frame_B (still valid)
├─ PULSE pri=20: Frame_P1 (just submitted)
└─ MANUAL pri=10: Frame_M

→ SELECT pri=30 (higher priority) → RENDER Frame_B

!!! LAMP COLOR CONFLICT !!!
Frame_B has LAMP merged from animation source
Frame_P1 has LAMP with pulse brightness from pulse task
→ pri=30 wins, PULSE is ignored

T=33.33ms:
┌─ ANIMATION pri=30: Frame_C(submitted)
├─ PULSE pri=20: Frame_P1
└─ MANUAL pri=10: Frame_M

→ SELECT pri=30 → RENDER Frame_C (PULSE still hidden)

T=50ms:
┌─ ANIMATION pri=30: Frame_D
├─ PULSE pri=20: Frame_P2(submitted, P1 evicted)
└─ MANUAL pri=10: Frame_M

→ SELECT pri=30 → RENDER Frame_D (PULSE still hidden)

...ANIMATION STOPS @ T=600ms...

T=700ms:
┌─ ANIMATION pri=30: Empty (Frame_N expired at T=600ms)
├─ PULSE pri=20: Frame_Pn (still valid, ttl=0.1s, timestamp=T-16.67ms)
└─ MANUAL pri=10: Frame_M

→ SELECT pri=20 (now highest) → RENDER Frame_Pn
LAMP now shows with pulse effect! (was hidden by ANIMATION)
FLOOR is missing → defaults to black!
LEFT still from Frame_M → red

!!! FLOOR DISAPPEARED !!!
This might be unexpected if user expects FLOOR to show something
when animation stops (should show as black)
```

---

## 8. Queue Memory Layout

### How Frame Queues Store Data

```
BEFORE ANIMATION STARTS:
┌────────────────────────────────┐
│ main_queues[30] (ANIMATION)    │
├────────────────────────────────┤
│ deque(maxlen=2)                │
│ Length: 0                      │
│ Capacity: 2 frames max         │
│                                │
│ [ ][ ]                         │
│      ↑                         │
│      Empty                     │
└────────────────────────────────┘

AFTER FIRST ANIMATION FRAME:
┌────────────────────────────────┐
│ main_queues[30] (ANIMATION)    │
├────────────────────────────────┤
│ deque(maxlen=2)                │
│ Length: 1                      │
│                                │
│ [Frame_A][ ]                   │
│                                │
│ Memory used: ~4KB per frame    │
│             × 2 max frames    │
│             = ~8KB per queue  │
└────────────────────────────────┘

AFTER SECOND ANIMATION FRAME:
┌────────────────────────────────┐
│ main_queues[30] (ANIMATION)    │
├────────────────────────────────┤
│ deque(maxlen=2)                │
│ Length: 2                      │
│                                │
│ [Frame_A][Frame_B]             │
│                                │
│ Queue is full!                 │
└────────────────────────────────┘

AFTER THIRD ANIMATION FRAME (PUSHED WHILE FULL):
┌────────────────────────────────┐
│ main_queues[30] (ANIMATION)    │
├────────────────────────────────┤
│ deque(maxlen=2)                │
│ Length: 2                      │
│                                │
│ [ ][Frame_B][Frame_C]          │
│                                │
│ Frame_A evicted (FIFO)         │
│ Memory freed and recycled      │
└────────────────────────────────┘
```

---

## 9. Hardware Rendering Timing

### DMA Transfer Visualization

```
FrameManager Render Loop @ 60 FPS (16.67ms per cycle):

Time (ms)  Action
──────────  ──────────────────────────────────────────────
0.00       Frame cycle starts
           _select_main_frame_by_priority()
           → Returns PixelFrame

0.05       _render_atomic() begins
           Convert Color objects to RGB tuples
           Call ZoneStrip.apply_pixel_frame()

0.10       WS2811 DMA TRANSFER STARTS
           Send 90 pixels × 24 bits = 2,160 bits
           @ 800kHz = 2.7ms

2.80       DMA TRANSFER ENDS
           Hardware latches pixels
           GPIO signal goes low (reset)

2.85       Reset time (50µs minimum)

2.90       Hardware ready for next frame
           Total time: 2.9ms

3.00       FrameManager still running
           Calculating next frame
           (13.67ms until next render)

16.67      Frame cycle ends
           Sleep complete, prepare next frame
           (time for next render)

33.34      Next frame rendered (similar timing)


TIMELINE SUMMARY:
┌─────────────────────────────────────────┐
│ Cycle Time: 16.67ms (60 FPS)            │
├─────────────────────────────────────────┤
│ [Work 0.10ms][DMA 2.70ms][Idle 13.87ms]│
│ ├─────────────────────────────────────┤ │
│ 0%       10%  20%  30% 100%           │ │
│ │        │    │    │  │               │ │
│ ├────────┼────────────────┤           │ │
│ CPU Active (83% idle)  │ Hardware DMA  │
│ ├────────┼────────────────┤           │ │
│           └─────────────────────────┬─┘ │
│                           Sleeping    │
└─────────────────────────────────────────┘

PRACTICAL IMPLICATIONS:
• 83% of CPU time is idle (waiting for next frame)
• DMA timing: 2.7ms (same for 90 pixels or 50 pixels)
• Theoretical max: 363 FPS (1000ms / 2.75ms)
• Practical max: ~150 FPS (CPU overhead)
• Current: 60 FPS (plenty of headroom)
```

---

## 10. Quick Reference: Zone Rendering Paths

### Which Frame Type for Each Source?

```
┌──────────────────────┬────────────────┬──────────────┐
│ Source               │ Frame Type     │ Priority     │
├──────────────────────┼────────────────┼──────────────┤
│ AnimationEngine      │ PixelFrame     │ 30 (ANIM)    │
│ StaticMode normal    │ ZoneFrame      │ 10 (MANUAL)  │
│ StaticMode pulse     │ ZoneFrame      │ 20 (PULSE)   │
│ TransitionService    │ PixelFrame     │ 40 (TRANS)   │
│ DebugPlayback        │ PixelFrame     │ 50 (DEBUG)   │
│ ColorCycleAnimation  │ FullStripFrame │ 30 (ANIM)    │
│ Preview Panel        │ PreviewFrame   │ varies       │
└──────────────────────┴────────────────┴──────────────┘

FRAME TYPE CHARACTERISTICS:

FullStripFrame:
  Use: Entire strip single color (all zones same)
  Content: {color: (r,g,b)}
  Rendering: Convert to zone dict (all zones = color)
  Example: ColorCycleAnimation

ZoneFrame:
  Use: Per-zone colors (each zone different)
  Content: {zone_id → Color}
  Rendering: Build pixel buffer from zone map
  Example: StaticModeController, PulseTask

PixelFrame:
  Use: Per-pixel control (complex patterns)
  Content: {zone_id → List[Color]}
  Rendering: Direct pixel-to-hardware mapping
  Example: SnakeAnimation, Breathe animation

PreviewFrame:
  Use: 8-pixel preview panel (separate GPIO)
  Content: {pixels: List[(r,g,b)]}
  Rendering: Direct pixel push (5V strip)
  Example: Mode indicators, debug
```

---

## 11. Summary: Data Flow Through System

```
┌─────────────────────────────────────────────────────────┐
│                  COMPLETE DATA FLOW                     │
└─────────────────────────────────────────────────────────┘

USER INPUT
(encoder turn, button press)
    │
    ▼
┌──────────────────────┐
│ Zone State Update    │ Update zone.state.color or brightness
│ ZoneService          │ Persist to state.json
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Frame Source         │ Generate frames based on new zone state
│ (Animation/Static)   │ Merge zones if animation
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Frame Submission     │ Add to priority queue[priority]
│ FrameManager queue   │ Async, non-blocking
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Frame Selection      │ Pick highest priority non-expired
│ Per-render cycle     │ Happens every 16.67ms @ 60 FPS
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Frame Rendering      │ Convert to pixel data
│ Type-specific path   │ (PixelFrame, ZoneFrame, etc.)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Hardware Update      │ Single DMA transfer
│ Atomic push to GPIO  │ All zones update simultaneously
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ LEDs Update          │ WS2811 protocol update
│ Hardware latches     │ Pixels visible to user
└──────────────────────┘
```
