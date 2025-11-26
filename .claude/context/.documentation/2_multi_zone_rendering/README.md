---
Last Updated: 2025-11-25
Updated By: Architecture Analysis
Changes: Initial comprehensive multi-zone rendering documentation
---

# Multi-Zone Rendering System Documentation

Complete analysis of how the Diuna LED control system combines multiple zones with different rendering states (static, animation, pulse, off) into a unified frame-based rendering pipeline.

## 📚 Documents in This Section

### 1. **[0_frame_combination_analysis.md](0_frame_combination_analysis.md)** - Core Architecture

**What to read**: First
**Time**: 20-30 minutes
**Key topics**:
- How multiple zones with different states are combined
- Frame merging in AnimationEngine
- Priority queue system and frame selection
- TTL (time-to-live) expiration handling
- Protection mechanisms for static zones
- Rendering frequency and hardware timing

**Best for**: Understanding the overall architecture

---

### 2. **[1_zone_state_diagrams.md](1_zone_state_diagrams.md)** - Visual Reference

**What to read**: Second (for visual learners)
**Time**: 15-20 minutes
**Key topics**:
- Complete data flow from zone state to hardware
- Priority-based frame selection flowchart
- State transition timelines with examples
- Frame queue memory layout
- Hardware DMA transfer timing
- Zone rendering path reference

**Best for**: Visual understanding of data flows and timing

---

### 3. **[2_optimization_guide.md](2_optimization_guide.md)** - Performance Improvements

**What to read**: Third (if optimizing)
**Time**: 15-20 minutes
**Key topics**:
- Frame change detection (95% DMA reduction)
- TTL customization per animation
- Zone masking for state preservation
- Priority ranges for fine-grained control
- Implementation roadmap and testing plans

**Best for**: Improving performance or UX

---

## 🎯 Quick Answers to Your Questions

### Q: How do we combine multiple zones in different rendering states?

**A:** Four mechanisms working together:

1. **AnimationEngine merges static zones** before frame submission
   - Animation yields pixels for animated zones only
   - Merges STATIC zone colors into frame before submit
   - Result: Complete frame with all zones

2. **Priority queues select highest-priority frame**
   - ANIMATION (pri=30) > PULSE (pri=20) > MANUAL (pri=10)
   - Only one frame per priority level selected per render cycle
   - Automatic fallback when high-priority source stops

3. **Frame rendering converts to atomic hardware update**
   - Complete pixel frame built from selected frame
   - Single DMA transfer to GPIO
   - All zones update simultaneously (no flicker)

4. **Zone states preserved through frame sources**
   - Static controller maintains zone color/brightness
   - Animation engine reads zone state at frame time
   - Fallback handles zones when source stops

**See**: [0_frame_combination_analysis.md](0_frame_combination_analysis.md) Section 2

---

### Q: Does the frame engine refresh at 60 FPS even when only static content?

**A:** **YES, FrameManager always runs at 60 FPS**, but:

- Frame **selection**: 60 times/sec ✓
- Hardware **rendering**: 60 times/sec ✓ (same pixels!)
- Frame **changes**: Only on user input ✗

**Current behavior**:
```
Static-only mode (no animation):
  Frame submission: ~0-1 per second (on user input)
  FrameManager cycles: 60 per second
  Hardware updates: 60 per second (identical pixels)
  Wasted DMA: ~95% of GPIO bandwidth
```

**Optimization opportunity**: Skip hardware DMA when frame hasn't changed
- See [2_optimization_guide.md](2_optimization_guide.md) **Optimization #1**

**See**: [0_frame_combination_analysis.md](0_frame_combination_analysis.md) Section 5

---

### Q: How do we prevent static zones from being overridden by animations?

**A:** Two-layer protection:

**Layer 1: Merging** (Primary Protection)
- AnimationEngine merges static zone colors **before submitting animation frames**
- Example: Animation frame includes `{FLOOR: animated, LAMP: white, LEFT: black}`
- Static zone colors captured at frame submission time
- Every animation frame is "complete" with all zones

**Layer 2: Priority Fallback** (Backup Protection)
- When animation stops, ANIMATION frames (pri=30) expire
- FrameManager falls back to PULSE (pri=20) or MANUAL (pri=10) frames
- Static zones remain visible even if animation source dies

**Result**: Static zones NEVER disappear, they always have a frame at some priority level

**See**: [0_frame_combination_analysis.md](0_frame_combination_analysis.md) Section 4

---

### Q: Do we have partial updates or optimization?

**A:** **No partial updates in current implementation**, but:

**Current approach**: All zones in every frame
- Static controller submits ALL zones (not just changed ones)
- Animation engine merges ALL zones
- Rendering always builds full 90-pixel frame
- Single DMA transfer to hardware

**Why it's acceptable**:
1. Hardware DMA time is limiting factor (2.7ms), not pixel count
2. Sending 90 pixels vs 50 pixels takes ~same time (WS2811 serial protocol)
3. 60 FPS rendering still easily achieved
4. CPU overhead minimal (83% idle time)

**Optimization opportunities**:
1. **Frame change detection** - Skip DMA when pixels unchanged (95% reduction)
2. **Zone masking** - Preserve zones not specified in frame (UX improvement)
3. **TTL customization** - Slower animations get longer TTL

**See**: [2_optimization_guide.md](2_optimization_guide.md) for all optimization details

---

## 🗂️ Navigation Guide

### For Understanding Current Architecture

1. Start: [0_frame_combination_analysis.md](0_frame_combination_analysis.md)
   - Read Section 1-4 for core concepts
   - Skim Section 8-9 for code paths

2. Visual Reference: [1_zone_state_diagrams.md](1_zone_state_diagrams.md)
   - Section 2 for data flow diagram
   - Section 3 for priority selection flowchart
   - Section 4-5 for timeline examples

3. Code: `/src/engine/frame_manager.py` and `/src/animations/engine.py`

---

### For Implementing Optimizations

1. [2_optimization_guide.md](2_optimization_guide.md)
   - Section 1-2: Current performance analysis
   - Section 2: Quick win optimization (Frame Change Detection)
   - Section 7: Implementation roadmap
   - Section 9: Testing guide

2. Code locations:
   - FrameManager: `/src/engine/frame_manager.py`
   - Animation merging: `/src/animations/engine.py:493-509`
   - Frame models: `/src/models/frame.py`

---

### For Troubleshooting Issues

| Issue | Section | Solution |
|-------|---------|----------|
| Zones turning black | [0_frame_combination_analysis.md](0_frame_combination_analysis.md) §8 | Zone masking optimization |
| Unexpected zone state during transitions | [1_zone_state_diagrams.md](1_zone_state_diagrams.md) §7 | Priority conflict analysis |
| Animation flicker | [0_frame_combination_analysis.md](0_frame_combination_analysis.md) §7 | Atomic rendering confirmation |
| Frame expiration issues | [1_zone_state_diagrams.md](1_zone_state_diagrams.md) §6 | TTL analysis and customization |

---

## 🔑 Key Concepts Summary

### Priority System
```
50 (DEBUG) > 40 (TRANSITION) > 30 (ANIMATION) > 20 (PULSE) > 10 (MANUAL) > 0 (IDLE)

Only HIGHEST priority non-expired frame is rendered each cycle
```

### Frame Types
```
PixelFrame    - Per-pixel control (animations)
ZoneFrame     - Per-zone colors (static, pulse)
FullStripFrame - All zones single color (color cycle)
```

### Frame Merging
```
AnimationEngine does it:
  1. Get zone state from ZoneService
  2. Merge STATIC zone colors into animation pixels
  3. Submit complete frame to FrameManager
```

### Rendering Pipeline
```
Zone State → Frame Source → Priority Queue → Selection → Rendering → Hardware DMA
                ↓
        (merging happens here)
```

### Timing
```
60 FPS target = 16.67ms per frame
Hardware DMA: 2.7ms per frame (WS2811 90 pixels)
CPU idle: 13.97ms per frame (83% idle)
```

---

## 📊 Performance Characteristics

### Current System

**Static-Only Mode** (most common):
- Frame submission: 0-1 per second
- FrameManager cycles: 60 per second
- Hardware DMA transfers: 60 per second
- CPU utilization: ~1-2% (mostly idle)
- Wasted DMA: 95% unnecessary transfers

**Animation Mode**:
- Frame submission: 60+ per second
- Hardware DMA: 60 per second
- CPU utilization: ~5-10% (animation computation + rendering)

### Optimization Opportunity

**After Frame Change Detection (#1)**:
- Static-only: DMA reduced by 95%
- Animation: No change (frames always different)
- Overall: ~16% reduction in GPIO overhead (system average)

---

## 🚀 Next Steps

### If You Just Want to Understand

1. Read [0_frame_combination_analysis.md](0_frame_combination_analysis.md) Sections 1-4
2. Look at [1_zone_state_diagrams.md](1_zone_state_diagrams.md) Section 2-4
3. Study `/src/engine/frame_manager.py` lines 100-120 (queue setup)
4. Study `/src/animations/engine.py` lines 493-509 (zone merging)

Time: ~1 hour for deep understanding

---

### If You Want to Optimize

1. Read [2_optimization_guide.md](2_optimization_guide.md) Sections 1-7
2. Implement Optimization #1 (Frame Change Detection) - 2 hours
3. Implement Optimization #5 (Frame Deduplication) - 1 hour
4. Test with static-only mode benchmarking

Expected result: 95% reduction in GPIO overhead

---

### If You're Debugging Issues

1. Identify symptom in [Troubleshooting Guide](#for-troubleshooting-issues)
2. Read relevant section
3. Check frame timelines in [1_zone_state_diagrams.md](1_zone_state_diagrams.md)
4. Use frame expiration analysis to find cause

---

## 🔗 Related Documentation

- **Architecture Overview**: `.claude/context/architecture/rendering-system.md`
- **Animation System**: `.claude/context/domain/animations.md`
- **Zone Management**: `.claude/context/domain/zones.md`
- **Hardware & GPIO**: `.claude/context/technical/hardware.md`
- **Code Standards**: `.claude/context/development/coding-standards.md`

---

## 📝 Terminology

- **Frame**: Complete pixel data for all LEDs at one moment in time
- **Priority Queue**: Collection of frames sorted by importance
- **TTL (Time-To-Live)**: How long a frame remains valid before expiring
- **Zone**: Logical grouping of adjacent LED pixels
- **Merge**: Combining data from multiple sources into single frame
- **DMA**: Direct Memory Access transfer from CPU to GPIO hardware
- **Atomic**: Single, indivisible operation (no interruption)
- **Flicker**: Visible update between different pixel states

---

## ✅ Quick Reference Checklist

**Understanding Frame Combination**:
- [ ] Read Section 1-4 of [0_frame_combination_analysis.md](0_frame_combination_analysis.md)
- [ ] Understand priority system (pri=30 ANIMATION > pri=10 MANUAL)
- [ ] Know how AnimationEngine merges zones
- [ ] Understand frame expiration mechanism

**For Code Review**:
- [ ] Check that all rendering goes through FrameManager (no direct `strip.show()`)
- [ ] Verify frame types are appropriate for source (PixelFrame vs ZoneFrame)
- [ ] Confirm TTL values are reasonable for frame source
- [ ] Look for manual zone-combining logic (should be in AnimationEngine)

**For Debugging**:
- [ ] Check frame queue status (any frames in queues?)
- [ ] Verify TTL values are reasonable
- [ ] Look at frame timestamps (are they current?)
- [ ] Check priority selection logic
- [ ] Use visual diagrams in Section 1-4 of [1_zone_state_diagrams.md](1_zone_state_diagrams.md)

---

**Last Updated**: 2025-11-25
**Status**: Complete analysis ready for implementation
**Next Phase**: Optimization (#1 and #5 recommended)