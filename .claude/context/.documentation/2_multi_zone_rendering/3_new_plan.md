┌────────────────────────────────────────┐
│  UI / User Actions                     │
│  Buttons, Encoders, Frontend           │
└────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  High-Level Engines                    │
│  AnimationEngine, PulseEngine,         │
│  TransitionEngine, PreviewEngine       │
└────────────────────────────────────────┘
                 │ submit frames
                 ▼
┌────────────────────────────────────────┐
│  FRAME MANAGER (Core)                  │
│  v4                                    │
│                                        │
│  • Priority Queues                     │
│  • Per-zone state buffer               │
│  • Frame merging                       │
│  • Final frame assembly                │
│  • Event-driven rendering              │
│  • Frame-by-frame debugging            │
└────────────────────────────────────────┘
                 │ final RGB buffers
                 ▼
┌────────────────────────────────────────┐
│  Hardware Mapping Layer                │
│  ZoneStrip (zone → pixels)             │
└────────────────────────────────────────┘
                 │ rgb pixel array
                 ▼
┌────────────────────────────────────────┐
│  WS281x Hardware Drivers               │
│  rpi-ws281x / neopixel                 │
└────────────────────────────────────────┘

# Overview

FrameManager v4 is a centralized LED rendering engine responsible for merging frames from multiple sources, maintaining per-zone render state, and producing the final pixel buffer for the hardware layer.

It introduces:

- a per-zone render buffer (ZoneRenderState)

- partial frame merging inside FrameManager

- event-driven rendering (render only on changes or scheduled ticks)

- a unified rendering pipeline for:

- animations

- transitions (crossfades, fade in/out, cuts)

- pulse effects

- manual static zones

- preview output

- asyncio-first design

- deterministic, flicker-free output with atomic DMA pushes

# Key Concepts

## 1. Separation: Domain State vs Render State

Do not conflate user domain state with runtime render state.

Domain state (ZoneState inside ZoneCombined)

Persisted in state.json

Holds user intent and configuration:

mode (STATIC / ANIMATION / OFF)

color (domain Color)

brightness

UI selection, parameters

Edited by controllers/services and saved

Render state (ZoneRenderState) — NEW

Runtime-only snapshot used by FrameManager while creating final frames

Contains:

pixels: List[Color] (logical per-zone pixel buffer)

brightness: float (effective brightness applied)

mode: ZoneRenderMode (effective at render time)

last_update_ts: float

source: FrameSource (which source last updated it)

dirty: bool (indicates if zone changed since last hardware push)

Not persisted; used only for merging & deciding minimal updates

Recommendation: Name the runtime class ZoneRenderState to avoid confusion.

## 2. Frame Types (atomic, domain-aware)

Frame types are domain-level objects (use Color, not raw tuples) until the last step. Example types:

FullStripFrame — one Color for whole strip

ZoneFrame — { ZoneID -> Color } (zone-level colors)

PixelFrame — { ZoneID -> List[Color] } (per-pixel colors)

PreviewFrame — 8-pixel list for preview zone

Frames carry metadata: priority, source, timestamp, ttl. Use TTL to avoid stale frames.

## 3. Priorities & Merge Rules

Priority order (higher wins):

```
IDLE (0) < MANUAL (10) < PULSE (20) < ANIMATION (30) < TRANSITION (40) < DEBUG (50)
```

Merge semantics (FrameManager merging model):

Select the highest-priority frame(s) for the strip.

If selected frame does not cover all zones (partial update), for each missing zone:

look down the priority ladder for the highest-priority frame that does include that zone

if none found, fall back to ZoneRenderState snapshot (last known rendered/persisted state)

The result is a complete per-zone pixel map for that render tick.

Convert per-zone Color → pixel buffer (apply brightness) once, at hardware boundary.

Send atomic full-frame to hardware (apply_frame/apply_pixel_frame) to avoid flicker.

This keeps animation code simple (animation yields only its zones) and moves the merging responsibility to FrameManager.

## 4. Event-driven vs Always-60Hz Rendering

Prefer event-driven rendering with optional periodic ticks:

FrameManager reacts to:

new frames submitted (immediate render or scheduled tick)

explicit frame-by-frame step requests

transitions that schedule multiple steps

For animations that need a steady cadence, the animation engine can either:

submit frames at desired cadence (FrameManager will render on arrival), or

request FrameManager to run a timed loop while animation active.

Static-only system should not continuously spam DMA; render only on change (or at low-frequency heartbeat if necessary).

Implementation note: keep a safe minimum inter-frame time based on WS2811 timing (≈2.75ms) and avoid violating DMA constraints.

## 5. Atomic Rendering — No Flicker Guarantees

Always produce and push a full physical pixel buffer per physical strip using a single hardware call:

Build final per-pixel frame (merge per-zone pixel lists, respecting reversed zones & multiple GPIO strips)

Apply ZoneStrip.apply_frame() / hardware.apply_frame() (single DMA transfer)

If apply_frame fails, use fallback of per-pixel set + single show() as last resort

This prevents partial updates and flicker at zone boundaries.

## 6. Preview Handling

Two valid approaches:

Preview as a virtual zone (recommended)
Add a ZoneID.PREVIEW with a small pixel count (e.g., 8) and treat preview frames as normal frames for that zone. Preview frames are just another source with priority (e.g., PREVIEW priority between MANUAL and PULSE or a dedicated preview queue).

Preview as separate physical target
If preview hardware is separate, keep separate preview queues/targets, but still merge preview frames similarly. This is slightly more complex.

Recommendation: treat preview as a normal zone in FrameManager merging — simplest and aligns with separation-of-concerns.

## 7. TTL & Fallbacks

Each frame has ttl. If a high-priority source stops producing frames, its frames will expire and the manager will automatically fall back to lower-priority frames or the ZoneRenderState snapshot.

Default TTL examples:

Animation: 100 ms (short)

Pulse: 100 ms

Manual/Static: 1500 ms (long)

Transition: 50–200 ms (configurable)

This avoids ghost frames and allows automatic fallback.

## 8. Frame-by-frame Mode (debugging)

Requirements:

Pause FrameManager rendering loop (or freeze submission)

Allow single-step advancement: FrameManager should render exactly one merged frame when step_requested toggled

AnimationEngine has a _frozen flag to stop submitting frames (or submit them with DEBUG priority)

FrameManager must be able to clear lower-priority frames to avoid flicker when stepping (helper clear_below_priority(min_priority))

## 9. Brightness & Color

Rule: keep Color as domain-level type; brightness is a separate property applied during final conversion to pixels.

Color (domain) represents color intent (HUE/PRESET/RGB)

brightness is a per-zone parameter (0–100%), stored in ZoneState

When building per-pixel buffers, call Color.to_rgb() then Color.apply_brightness(r,g,b, brightness) at the last possible stage (FrameManager → ZoneStrip boundary)

For transitions and animations that rely on brightness modulation (e.g., breathe, fade), operate on either:

color brightness factor (multiply RGB), or

separate brightness parameter depending on animation semantics

Do not push brightness down into hardware IPhysicalStrip as a persistent concept; keep hardware API accepting raw Color/RGB and a separate show().

## Minimal API Sketch (conceptual)

```python
# Frame submission (domain-typed)
await frame_manager.submit_pixel_frame(PixelFrame(priority=ANIMATION, zone_pixels={ZoneID.FLOOR: [Color.from_hue(0), ...]}))

# FrameManager internal merge (per tick)
final_per_zone_pixels = {}
selected = pick_highest_priority_frame()

for zone in all_zones:
    if selected.covers(zone):
        final_per_zone_pixels[zone] = selected.pixels_for(zone)
    else:
        # find lower-priority frame that covers this zone
        fallback = find_highest_lower_priority_frame_covering(zone)
        if fallback:
            final_per_zone_pixels[zone] = fallback.pixels_for(zone)
        else:
            final_per_zone_pixels[zone] = zone_render_state[zone].pixels

# Convert to physical per-pixel list for each ZoneStrip
for strip in zone_strips:
    full_frame = strip.build_frame_from_zones(final_per_zone_pixels)
    strip.apply_pixel_frame(full_frame)

```

## Advantages of FrameManager-side merging

Clean separation: animation/pulse/transition authors only provide their effect for the zones they control

Single place for deterministic merge logic

Easier to implement partial updates and preview as a zone

Simplifies animation engine (no need to merge static zones every frame)

Single source of truth for final render decisions

## Trade-offs

FrameManager is more complex (needs zone-aware merging)

FrameManager must know zone layout & lengths (it already knows registered ZoneStrip instances and mappers)

Slight CPU overhead of merging — acceptable compared to DMA cost

## Implementation Checklist / To-Do

Add ZoneRenderState class (runtime per-zone buffer)

Change frame models to use Color (domain) in PixelFrame.zone_pixels and ZoneFrame.zone_colors

Make FrameManager merging algorithm:

accept partial frames

merge with lower priorities and ZoneRenderState

Ensure conversion to RGB + brightness happens at ZoneStrip boundary (build_frame_from_zones should accept Color values and brightness when building physical frame)

Support preview as virtual zone or separate preview queue (prefer virtual zone)

Keep TTL semantics and frame-by-frame debug hooks

Keep WS281x timing and atomic apply_frame semantics

Provide tests for merging, TTL expiration, preview, and frame-by-frame stepping

### Example ZoneRenderState (suggested)

```python
@dataclass
class ZoneRenderState:
    zone_id: ZoneID
    pixels: List[Color]               # logical pixels for the zone (Color objects)
    brightness: int                   # 0-100
    mode: ZoneRenderMode
    source: FrameSource | None
    last_update_ts: float = field(default_factory=time.time)
    dirty: bool = True
```

## Final Notes

This architecture preserves your separation of concerns: animations produce only the frames for zones they control; FrameManager composes final output.

Keep Color domain-heavy until the hardware boundary; convert to RGB and apply brightness only at the last step.

FrameManager must be the single place that knows how to compose zones into physical strips (it already has ZoneStrip registration and zone mappers).

This design keeps the LED output deterministic and simplifies adding features (preview, new priorities, networked frames) in future.
