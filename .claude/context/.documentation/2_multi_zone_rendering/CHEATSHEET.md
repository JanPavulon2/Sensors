---
Last Updated: 2025-11-25
Updated By: Architecture Analysis
Changes: Quick reference guide for multi-zone rendering
---

# Multi-Zone Rendering: Quick Reference Cheatsheet

## 1. Frame Priority System (One-Liner)

**"ANIMATION wins over PULSE wins over MANUAL"**

```
DEBUG=50 > TRANSITION=40 > ANIMATION=30 > PULSE=20 > MANUAL=10 > IDLE=0
```

## 2. How Zones are Combined

```
Zone State (color, brightness, mode)
  ↓
AnimationEngine.merge_zones()
  ↓
PixelFrame {all_zones: merged_data}
  ↓
FrameManager.select_by_priority()
  ↓
Hardware.apply_frame()
  ↓
LEDs update (ATOMIC - no flicker)
```

## 3. Frame Sources Responsibility

| Source | Responsibility | What NOT to do |
|--------|-----------------|---|
| **AnimationEngine** | Merge ALL zones (animated + static) into frame | Don't let static zones be missing |
| **StaticController** | Submit complete zone dict (all zones) | Don't submit partial zones |
| **PulseTask** | Submit zone with pulse brightness | Don't call `strip.show()` directly |

## 4. Current Behavior: 60 FPS Always

```
┌─────────────────────────────────────────┐
│ FrameManager._render_loop() @ 60 FPS   │
│                                         │
│ Every 16.67ms:                          │
│  1. Select highest priority frame       │
│  2. Render to hardware (2.7ms DMA)     │
│  3. Sleep remaining time               │
│                                         │
│ Result:                                 │
│  Same pixels sent 60× per second        │
│  even if nothing changed!               │
└─────────────────────────────────────────┘
```

## 5. Frame Expiration Timeline

```
Frame submitted at T=0ms, ttl=100ms
T=50ms:  Still valid (50 < 100)
T=100ms: Still valid (100 = 100)  ← borderline
T=101ms: EXPIRED (101 > 100) ✗
         Render falls back to next priority
```

## 6. Static Zone Protection (Two Ways)

### Way 1: Merging (Primary)
```
if zone.mode == STATIC:
    frame.zone_pixels[zone_id] = zone.color  # Include in frame
```

### Way 2: Fallback (Backup)
```
if animation_stops():
    animation_frames_expire()  # After 100ms TTL
    pulse_frame_rendered()     # Falls back to PULSE pri=20
    # → Zone still visible!
```

## 7. Performance Wasted

**In Static-Only Mode**:
```
Scenario: User sets LAMP to white, nothing animates

Frame 1:  Submit ZoneFrame(LAMP=white) @ T=0ms, ttl=1.5s
          Render to hardware (2.7ms DMA)

Frame 2-89: Select SAME ZoneFrame (not expired)
            Render to hardware (2.7ms DMA) ← Same pixels!
            Repeat 89 times

Total wasted: 89 × 2.7ms = 240ms per second
              = 24% of DMA bandwidth
              = 95% of static-mode updates
```

**Optimization**: Check if frame changed before DMA
- See [2_optimization_guide.md](2_optimization_guide.md)

## 8. Key Frame Types

```python
PixelFrame          # Per-pixel control (animations)
  zone_pixels: {FLOOR: [Color, Color, ...], ...}

ZoneFrame           # Per-zone colors (static, pulse)
  zone_colors: {FLOOR: Color, LAMP: Color, ...}

FullStripFrame      # All zones single color
  color: (r, g, b)
```

## 9. When Zones Turn Black (Problem)

**Scenario**: ANIMATION frame expires, PULSE takes over

```
T=0-600ms:  ANIMATION frame (pri=30)
            {FLOOR: animated, LAMP: white, LEFT: black}

T=600ms:    Animation stops, no new ANIMATION frames

T=700ms:    ANIMATION frame expires
            Select PULSE frame (pri=20)
            {LAMP: white}  ← only LAMP!

Result:     FLOOR and LEFT default to black!
            ⚠️ Unexpected (should preserve previous state)
```

**Solution**: Zone masking (See Optimization #2)

## 10. Implementation Locations

| What | File | Lines |
|------|------|-------|
| **Queue setup** | `src/engine/frame_manager.py` | 100-110 |
| **Frame selection** | `src/engine/frame_manager.py` | 318-338 |
| **Zone merging** | `src/animations/engine.py` | 493-509 |
| **Rendering** | `src/engine/frame_manager.py` | 400-450 |
| **Hardware DMA** | `src/zone_layer/zone_strip.py` | 175-191 |
| **Frame models** | `src/models/frame.py` | 40-90 |

## 11. Debugging Checklist

```
[ ] Are frames being submitted? (check queue size)
[ ] Is frame expired? (check TTL: timestamp - now > ttl?)
[ ] Which frame selected? (check priority, highest priority should win)
[ ] Are zones being merged? (check for StaticFrames alone)
[ ] Is hardware updating? (check DMA calls)
[ ] Is flicker happening? (should never happen - atomic)
```

## 12. Architecture Strengths ✅

```
✓ Multiple sources don't conflict (priority arbitration)
✓ Expired frames cleaned up automatically (TTL)
✓ Static zones protected from overrides (merging + fallback)
✓ No flicker (atomic DMA updates)
✓ Fire-and-forget submission (non-blocking)
✓ Simple and maintainable
```

## 13. Architecture Weaknesses ❌

```
✗ Redundant DMA in static-only mode (95% waste)
✗ Zones default to black when frame missing (UX issue)
✗ No partial updates (always full strip)
✗ Fixed TTL per source type (not adaptive)
```

## 14. Optimization Options (Priority Order)

| # | Name | Effort | Value | Status |
|---|------|--------|-------|--------|
| 1 | Frame Change Detection | 2h | High | 🟢 **DO NOW** |
| 5 | Frame Dedup | 1h | Med | 🟢 **DO NOW** |
| 3 | Custom TTL | 3h | Med | 🟡 **If needed** |
| 2 | Zone Masking | 6h | Med | 🟡 **If UX issue** |
| 4 | Priority Ranges | 4h | Low | 🔴 **Skip** |

## 15. 60 FPS Rendering: Good or Bad?

**Good**:
- Smooth animations look great
- 60 FPS well-supported by WS2811 hardware

**Bad**:
- Wastes power in static-only mode (95% of updates identical)
- CPU stays busy checking every 16.67ms

**Solution**: Frame change detection (Optimization #1)

## 16. Frame Merging in AnimationEngine

**Before Submit** (current code):
```python
for zone in self.zones:
    if zone.state.mode == STATIC:
        # Add static zone to frame
        zone_pixels_dict[zone.id] = [color] * length
```

**Key Point**: Merging happens BEFORE submission to FrameManager
- Not FrameManager's job
- Animation engine's responsibility
- Keeps FrameManager simple

## 17. Queue Memory Management

```
Each priority level: deque(maxlen=2)
  Max capacity: 2 frames per priority

Result:
  Old frames automatically evicted (FIFO)
  Memory usage bounded
  Latest 2 frames always available
  No manual cleanup needed
```

## 18. TTL Values at a Glance

```
Animation frame:   ttl=0.1s  (expires in 6 frames @ 60 FPS)
Pulse frame:       ttl=0.1s  (expires in 6 frames)
Transition frame:  ttl=0.1s  (expires in 6 frames)
Static frame:      ttl=1.5s  (expires in 90 frames - LONGER!)
Debug frame:       ttl=5.0s  (manual stepping)

Why longer for static?
  Animation submits new frames every cycle (~6ms)
  Static submits new frames only on user input (seconds apart)
  Longer TTL prevents premature expiration
```

## 19. Common Misconceptions ❌

**"Zones update independently"**
- ❌ Wrong: All zones update together (atomic)
- ✅ Correct: Single frame submitted, all zones in it

**"I can call strip.show() from my code"**
- ❌ Wrong: Breaks architecture, causes flicker
- ✅ Correct: Submit to FrameManager only

**"Static zones are protected from animation"**
- ✅ Correct: Merged into animation frames + fallback priority

**"Frame Manager picks best frame for each zone"**
- ❌ Wrong: Picks one frame for ENTIRE strip
- ✅ Correct: Single highest-priority frame rendered

**"60 FPS rendering is efficient"**
- ❌ In static mode: 95% wasted DMA
- ✅ In animation: Necessary for smooth motion

## 20. Real-World Scenario: Multi-Zone Rendering

```
Setup:
  FLOOR: Snake animation (fast)
  LAMP: White static with pulse (medium)
  LEFT: Static red (no pulse)

Frame Timeline:
  T=0:    AnimationEngine merges:
          {FLOOR: [anim], LAMP: [white], LEFT: [red]}
          @ ANIMATION pri=30

          PulseTask submits:
          {LAMP: [white@80%]}
          @ PULSE pri=20

  Result: ANIMATION pri=30 selected (higher)
          → FLOOR shows animation
          → LAMP shows white@original (not pulsing!)
          → LEFT shows red

  ⚠️ PULSE hidden because ANIMATION pri=30 > PULSE pri=20
  (This is correct behavior - animations take priority)

  T=600ms: Animation stops
           ANIMATION frame expires (100ms TTL)

  T=700ms: PULSE pri=20 now selected
           → FLOOR turns black (not in PULSE frame)
           → LAMP shows white@80% (pulsing!)
           → LEFT turns black (not in PULSE frame)

  ⚠️ FLOOR and LEFT disappeared!
  This is the "zone masking" problem (Optimization #2)
```

---

**Need more details?** Read [0_frame_combination_analysis.md](0_frame_combination_analysis.md)
**Need visuals?** See [1_zone_state_diagrams.md](1_zone_state_diagrams.md)
**Want to optimize?** Check [2_optimization_guide.md](2_optimization_guide.md)