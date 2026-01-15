---
Last Updated: 2025-11-25
Type: User Documentation
Purpose: Understanding the frame priority system, TTL, and atomic rendering
---

# Frame Priority System

## The Problem: Multiple Sources Want to Control LEDs

Imagine multiple effects trying to control the same LED simultaneously:
- Animation running on a zone
- Transition fading out
- Pulsing effect (edit mode)
- Static color set by user

Which one wins? How does the system decide?

**The Solution**: Priority-based frame selection.

## Frames

A **frame** represents the complete or partial LED state at one moment in time.

### Frame Types

**ZoneFrame**:
- Specifies colors for entire zones
- Used by animations and static modes
- Data: `{zone_id: Color, zone_id: Color, ...}`

**PixelFrame**:
- Specifies colors for individual pixels
- Used by pixel-based animations
- Data: `{zone_id: [pixel_colors], zone_id: [pixel_colors], ...}`

**PreviewFrame**:
- Specifies colors for preview panel (8 pixels)
- Used by preview visualization
- Data: `[pixel_colors, ...]`

### Frame Properties

**Priority**:
- Integer value (0-100)
- Higher priority wins over lower
- Multiple frames with same priority: highest TTL selected

**TTL** (Time-To-Live):
- How long the frame remains valid
- Frames older than TTL are discarded
- Typical: 100ms for most frames
- Prevents "ghost pixels" (stale effects lingering)

**Source**:
- Who submitted the frame (animation, transition, static, etc.)
- Used for debugging and priority assignment

**Timestamp**:
- When frame was created
- Used for TTL expiration calculation

## Priority Levels

The system uses semantic priority levels. Higher number = higher priority.

```
Priority  Level         Purpose                 Sources
────────  ─────         ───────                 ───────
50        DEBUG         Debugging/testing       Debug tools
40        TRANSITION    Smooth state changes    Transition service
30        ANIMATION     Normal animations       Animation engine
20        PULSE         Edit mode pulsing       Static mode controller
10        MANUAL        Static user colors     Static mode controller
0         IDLE          Default/empty state     System default
```

### Priority Semantics

**IDLE (0)**: Empty state, lowest priority
- Used when nothing else is rendering
- Results in black/off LEDs

**MANUAL (10)**: Static colors set by user
- User edited FLOOR to red in STATIC mode
- Renders unless something higher priority takes over

**PULSE (20)**: Edit mode pulsing effect
- Zone pulses while user is editing it
- Overrides static color of that zone

**ANIMATION (30)**: Normal animations
- Breathe effect, snake, color fade, etc.
- Overrides static colors
- Typical during normal operation

**TRANSITION (40)**: Smooth transitions
- Fade out, fade in, crossfade
- Overrides animations temporarily
- Used for mode switches, power on/off

**DEBUG (50)**: Debugging frames
- Special frames for testing
- Overrides everything

### Resolution Examples

**Example 1: Animation vs Static**
```
FLOOR zone receives frames:
├─ ZoneFrame (priority 10): FLOOR = red (static)
└─ ZoneFrame (priority 30): FLOOR = animated blue (breathing)

Selection process:
1. Check all frames
2. Filter out expired (neither expired yet)
3. Priority 30 > 10
4. Result: Display animated blue
```

**Example 2: Transition overrides everything**
```
System state:
├─ Animation (priority 30): Breathe animation
├─ Static (priority 10): Red color
└─ Transition (priority 40): Fade to black

Selection:
1. Check all frames
2. All valid, none expired
3. Priority 40 (transition) > 30 (animation)
4. Result: Display fade-to-black (overrides both)
```

**Example 3: Multiple animations (independent zones)**
```
System has:
├─ FLOOR animation (priority 30): Snake effect
├─ LEFT animation (priority 30): Breathe effect
└─ RIGHT static (priority 10): Green color

Frame selection is per-type:
├─ ZoneFrame selection: Highest priority ZoneFrame wins
└─ PixelFrame selection: Highest priority PixelFrame wins

Result:
├─ FLOOR: Snake (pixel-based animation)
├─ LEFT: Breathe (zone-based animation)
└─ RIGHT: Green (static zone frame)

All three rendered together! (each type has own priority queue)
```

### Priority in Practice

**Normal operation**:
```
Static mode, FLOOR red, LEFT blue
├─ Static: FLOOR red (priority 10), LEFT blue (priority 10)
└─ Animation: None
Result: FLOOR red, LEFT blue
```

**Animation started on FLOOR**:
```
├─ Static: FLOOR red (priority 10), LEFT blue (priority 10)
└─ Animation: FLOOR breathing red (priority 30)
Result: FLOOR breathing, LEFT blue
(Animation overrides static for FLOOR only)
```

**Edit mode pulsing FLOOR**:
```
├─ Static: FLOOR red (priority 10)
├─ Animation: FLOOR breathing (priority 30)
└─ Pulse: FLOOR pulsing (priority 20)
Result: FLOOR pulsing
(Pulse overrides both animation and static)
```

**Power transition active**:
```
├─ All current effects...
└─ Transition: Fade to black (priority 40)
Result: Entire system fades to black
(Transition overrides everything)
```

## TTL (Time-To-Live) System

**Problem**: What if a component crashes or stops submitting frames? Stale data might remain forever.

**Solution**: Every frame has a TTL. Frames older than their TTL are discarded.

### TTL Timeline

```
Time 0ms:    Frame submitted, TTL = 100ms
Time 50ms:   Frame is 50ms old, still valid
Time 100ms:  Frame is 100ms old, expires (discarded)
Time 101ms:  Frame no longer in system
```

### TTL Duration by Priority

**Typical values**:
- Most frames: ~100ms
- Transitions: May be longer (smooth fadeout takes time)
- Debug frames: Varies based on use case

### TTL Protection

**Scenario: Animation crashes**
```
Before:
├─ Animation submits frames every 16.67ms
├─ LEDs display animation
└─ Controller running

Crash occurs (animation task stops)
│
After crash (first 100ms):
├─ Last frame still in queue (TTL valid)
├─ FrameManager still selects and renders it
└─ LEDs continue showing last animation frame

After 100ms (frame expires):
├─ Frame removed from queue
├─ Next frame (if any) selected
├─ If no other frames, displays IDLE (black)
└─ LEDs go dark (no stale ghost pixels)
```

**Prevents**:
- Ghost pixels (stale animation effects lingering)
- Undefined behavior (old data overriding newer)
- Hardware lockup (stale commands repeated)

## Atomic Rendering

**Definition**: All LEDs update together, in a single DMA transfer.

### Why Atomic?

**Without atomic rendering**:
```
Frame 1: Set FLOOR to red (5ms)
Frame 2: Set LEFT to blue (5ms)
User sees:
├─ For first 5ms: FLOOR red, LEFT black (not yet updated)
├─ Flicker/jitter (transitions don't look smooth)
└─ Inconsistent state visible to user
```

**With atomic rendering**:
```
Frame 1+2 combined:
├─ FLOOR red
├─ LEFT blue
└─ All sent in single DMA (< 1ms)

User sees:
├─ Instant, smooth update
├─ No flicker or jitter
└─ Consistent state
```

### Implementation

**FrameManager's render cycle**:
```
1. Select highest priority frame (or frames)
2. Convert to pixel array (all zones)
3. Load into DMA buffer (software operation)
4. Call zone.show() ONCE (hardware operation)
   └─ Single DMA transfer sends all pixels
5. Wait for next render cycle
6. Repeat
```

**Result**: All 90+ pixels update in ~2.75ms, together.

## Render Cycle

The render cycle runs at **60 FPS** (every 16.67ms):

```
0ms     |  5ms    | 10ms    | 15ms    | 16.67ms |  ...
        |         |         |         |         |
Frame N | Process | Convert | DMA Xfer| Next -> |
selected| data    | to pixels|to LEDS  | cycle   |
        |         |         |         |         |
        <------------ ~15ms of work ---------->
```

### Timing Constraints

**WS2811 LED timing**:
- Minimum frame time: 2.75ms (DMA transfer for 90 pixels)
- Reset time: 50µs (required between frames)
- Target FPS: 60 (16.67ms per frame)

**Headroom**: 16.67ms - 2.75ms = 13.92ms per cycle
- Used for: frame selection, conversion, processing
- Provides ~40% safety margin

### Frame Rate Management

**60 FPS is target, not guaranteed**:
- If processing takes too long, next frame delayed
- System adapts (drops frame if needed)
- Visible as occasional refresh stutter
- Usually not noticeable (smooth animations continue)

## Frame Selection Algorithm

**Complete selection process per render cycle**:

```
1. Get timestamp (current time)

2. Scan all submitted frames
   for each frame:
     if (current_time - frame.timestamp) > frame.ttl:
       mark frame as expired
     else:
       keep frame

3. Group remaining frames by type:
   ├─ ZoneFrames
   ├─ PixelFrames
   └─ PreviewFrames

4. For each group, select highest priority:
   highest_zone_frame = max(zone_frames, key=priority)
   highest_pixel_frame = max(pixel_frames, key=priority)
   highest_preview_frame = max(preview_frames, key=priority)

5. Render selected frames:
   ├─ Convert frames to pixel arrays
   ├─ Merge pixels from multiple frames
   ├─ Apply zone brightness
   └─ Load into DMA buffer

6. Hardware update:
   led_channel.show()

7. Return to step 1 (repeat 60 times per second)
```

## Frame Submission

**Components submit frames to FrameManager**:

```python
# Static mode controller
zone_colors = {FLOOR: Color.red(), LEFT: Color.blue()}
frame = ZoneFrame(zones=zone_colors, priority=MANUAL)
await frame_manager.submit_zone_frame(frame)

# Animation engine
zone_colors = {FLOOR: Color.breathing_red()}
frame = ZoneFrame(zones=zone_colors, priority=ANIMATION)
await frame_manager.submit_zone_frame(frame)

# Transition service
frame = PixelFrame(pixels=[...all pixels...], priority=TRANSITION)
await frame_manager.submit_pixel_frame(frame)
```

**Submission is asynchronous**:
- Non-blocking to submitter
- FrameManager stores in internal queue
- Submitter continues immediately

## Summary

**Priority System**:
- Resolves conflicts between multiple effects
- 6 semantic levels (IDLE to DEBUG)
- Highest priority wins each render cycle

**TTL System**:
- Prevents stale data lingering
- Default ~100ms
- Automatic cleanup

**Atomic Rendering**:
- All LEDs update together
- Single DMA transfer per cycle
- No flicker or jitter

**Frame Selection**:
- Happens 60 times per second
- Filters expired frames
- Selects highest priority per type
- Merges results for rendering

**Result**: Clean conflict resolution, no coordination needed between components, smooth visual updates.

---

**Next:** [Extending the System](6_extending_system.md)
