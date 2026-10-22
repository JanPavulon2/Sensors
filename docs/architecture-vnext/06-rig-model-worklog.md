# Rig Model — Work Log (2026-09-11 / 2026-09-12)

Covers two days of work: finishing the ESP32↔RPi5 roadmap (Phases 4–8) and then
replacing the hardware assumptions it was built on with a real rig model.

Companion docs: `03-led-taxonomy.md` (now implemented), `04-capabilities.md`
(capabilities are now derived), `05-esp32-rpi-roadmap.md` (phase detail).

---

## Part 1 — ESP32 ↔ RPi5, Phases 4–8

Executed from `docs/superpowers/plans/2026-09-06-esp32-rpi-phases-4-8.md` (29 tasks).

### What shipped

| Phase | Result |
|---|---|
| 4 — Real commands | `HttpNodeTransport`, `Esp32CommandDevice`, `NodeCommandRouterDevice`, `NodeRegistryService` owning a `HostEngine`; firmware `/command` WebServer |
| 5 — Capabilities | `core/capabilities.py` vocabulary mirroring `04-capabilities.md` |
| 6 — Remote zones | State-streaming pipeline (not frames); `zone.state` command; firmware applies colour/brightness/on-off |
| 7 — Multi-node sync | `MultiNodeSyncBroadcaster`, NTP + UDP multicast phase reference at `239.255.10.10:41234` |
| 8 — Hardening | Socket.IO `nodes:snapshot`/`node:snapshot`, ArduinoOTA, systemd unit |
| Frontend | New `/nodes` page, `features/nodes/` mirroring the `features/zones` realtime pattern |

### Bugs found and fixed along the way

- **`HttpNodeTransport.send()` killed the whole command system.** It ran inside
  `HostEngine`'s single shared consumer loop (`core/event_bus.py`'s `run()`, which
  has no try/except). One unreachable ESP32 raised, the loop died, and command
  delivery to *every* node stopped silently for the rest of the process's life.
  Caught only by live testing — noticed because shutdown reported one fewer
  background task than expected. Now swallows and logs.
- **Registration ordering crash.** `register_device()` raises if its node isn't
  already in `HostEngine.nodes`, so `register_node()` has to come first for a
  brand-new node. Found during plan review, before execution.
- **`Color.from_request()` used `typing.Tuple` as a constructor** instead of the
  builtin `tuple` (`src/models/color.py`). Pre-existing, affected *any* RGB colour
  set including local zones. Surfaced as a live 500.
- **Two frontend test-infra gaps that had never been exercised**: `vitest.config.ts`
  had empty `setupFiles` (so `@testing-library/jest-dom` matchers never worked), and
  jsdom lacks `ResizeObserver` (needed by the canvas `HueWheelPicker`). Both fixed in
  `frontend/src/test/setup.ts`.

### Environment findings

- `sudo` is permanently unavailable from VS Code's integrated terminal: Remote-SSH
  sets `no_new_privs` on every spawned process. Not a container, not fixable in code.
  Use a plain SSH session or the systemd unit (`deploy/`).
- `pio device monitor` fails non-interactively (`termios.error`); a raw `pyserial`
  read works fine.
- The shared secret moved to a gitignored `deploy/diuna-backend.env`.

---

## Part 2 — The problem Phase 6 left behind

Phase 6 was built on one assumption baked in everywhere: *an ESP32 drives one
30-pixel addressable WS2812 strip*. The actual hardware is **a single diode driven
by one MOSFET channel**.

Consequences, all real and all live:

- `esp32_zones.yaml` claimed `pixel_count: 30` for one LED
- `GET /nodes/{id}` reported `addressable_pixels` + `color_control_rgb` — **both false**
- The UI offered a colour picker for a diode whose colour is a fixed physical property
- `led_config.h` chose the output path with a **compile-time `#if`**
- Remote zone state was RAM-only — every backend restart silently reset it
- Remote zones had no live preview at all

Underneath: Phase 4–8 had used the core's *runtime* half (`Device`, `Port`,
`Message`, `HostEngine`, `NodeTransport`) and skipped the *declarative* half
(`DeviceDefinition`, `DeviceInstance`, `Peripheral`, `PeripheralType`,
`PortDefinition`/`SignalType`) — the designed-but-not-yet-consumed model. That is
precisely why hardware facts ended up hardcoded in a Python list and a YAML file
with a single `pixel_count` field.

---

## Part 3 — The rig model

This chapter is that declarative half's first consumer. It does **not** introduce a
parallel model.

### Core additions (the designed-but-missing pieces)

| File | What |
|---|---|
| `core/hardware_control_interface.py` | `ANALOG_PWM` / `ADDRESSABLE_DATA` / `CONSTANT_CURRENT_DRIVER` (doc 03, listed under Core in doc 01) |
| `core/module.py` | **`Module`** — doc 01's middle aggregate, the one level that had no file. A MOSFET board is a Module of several `MOSFET_CHANNEL` Peripherals |
| `core/light.py` | `LightComponentType`, `WhiteProfile`, `ChannelRole`, `ChannelBinding`, `LightFixture` |
| `core/capability_derivation.py` | Capabilities computed, never declared |

Reused as-is, finally: `peripheral_type.py` (`MOSFET_CHANNEL`, `WHITE_LED`,
`RGB_LED`, `ARGB_LED` — already the exact vocabulary), `peripheral.py`,
`device_definition.py`, `device_instance.py`, `port_definition.py`.

Settled one inconsistency: `DeviceDefinition.id` was `str` but
`DeviceInstance.definition_id` was `UUID`. Both are now `str` slugs — definitions
are a hand-authored catalog that appears verbatim in config and API payloads.

### The distinction that makes it work

`component_count` (LEDs that physically emit) vs `addressable_group_count`
(independently drivable units). That one pair separates every supported shape with
no special cases:

```
single diode on a MOSFET        1   / 1
COB white strip on a MOSFET     320 / 1     ← hundreds of LEDs, one dimmer
analog RGB strip on 3 MOSFETs   150 / 1     ← real colour, still one "pixel"
WS2812 strip                    30  / 30
single WS2812 pixel             1   / 1
```

### Capabilities are derived, not declared

`ESP32_LED_STRIP_DEVICE_CAPABILITIES` is gone. Derived from
(control interface × component type × channel bindings):

```
caps = {switch_binary}
dimmable interface                              -> + dimming
RGB  fixture, ≥3 colour-role channels bound     -> + color_control_rgb
RGBW fixture, ≥3 colour + a WHITE channel       -> + color_control_rgbw
ADDRESSABLE_PIXEL fixture                       -> + color_control_rgb
  …and addressable_group_count > 1              -> + addressable_pixels
```

Zone capabilities = **intersection** over its fixtures — a zone drives everything
with one shared state, so it can only offer what all of them support.

**The UI is generated from this set.** One adaptive panel, not one component per
hardware type. A single white diode advertises `{switch_binary, dimming}`, so no
colour picker is ever rendered — and `PUT …/color` returns **409**, not a silent 204.

### Rig storage

- `src/config/rig.yaml` — catalog (blueprints) + bootstrap wiring. Read only when
  `rig.json` doesn't exist yet.
- `src/state/rig.json` — the editable half, written by `RigService` using the same
  debounced-save pattern as `ApplicationStateService`. Now gitignored.
- `RigService` validates every edit: bindings must reference channels that exist,
  a fixture can't be driven from a different node, a driver still in use can't be
  deleted.

### Convergence instead of acknowledgements

Per-command acks can't work here — `HttpNodeTransport.send()` must never raise or
block inside the shared consumer loop (see Part 1). So:

1. desired state is **persisted** in `rig.json` → restart no longer resets anything
2. firmware **echoes** its applied state in the existing 5 s heartbeat
3. `RemoteZoneStateService.reconcile_node()` compares and **re-pushes on mismatch**
4. `HttpNodeTransport` records per-node delivery success → `last_command_delivered`
   on the node snapshot, so the API stops implying success for an unplugged node
5. the UI shows "Not confirmed by the device — retrying" when `in_sync` is false

One mechanism covers offline nodes, ESP32 reboots, dropped commands and restarts.

`RemoteZoneRenderBridge` → **`RemoteZoneStateService`** (it neither rendered nor
bridged), and the missing `set_render_mode()` finally exists — the firmware had
supported BREATHE all along with no backend method, route or control to reach it.

### Live preview

Remote zones stream state, not frames, so there was nothing to preview.
`RemoteFixtureAnimator` reproduces host-side exactly what each fixture is emitting —
deliberately mirroring the firmware's own maths (triangle-wave breathe over the
shared NTP cycle; identify blink at the firmware's 150 ms interval). Identify is
host-initiated, so the host knows to blink the preview too.

Merged into the **existing published frame stream** rather than a new channel:
`FrameStreamer._serialize()` now accepts string keys alongside `ZoneID`, and emits
even when the queue is empty so a remote breathe doesn't freeze on screen while
`FrameManager` is idle. The animator does not push frames itself — `FrameManager`
owns the cadence and the queue is `maxlen=2`, so a second producer would just
overwrite it.

### Firmware: runtime config, not a compile flag

- `#if USE_ADDRESSABLE_STRIP` → a runtime `OutputConfig` held in NVS (`Preferences`)
- New `node.config` command applies and persists it; `led_config.h` is now
  **fallback only**, so an unprovisioned board still lights up
- `applyOutputColor()` gained the 3-channel analog RGB path (one `ledcWrite` per
  R/G/B) beside the single-channel `max(r,g,b)` path and the FastLED path
- Heartbeat now carries `applied_state` and `config_version`
- **Known limit:** FastLED takes its data pin as a template parameter, so the
  addressable path only works on pins the build was compiled for (currently 4, 5,
  16, 18). The analog PWM path accepts any GPIO.

`NodeConfigurationPusher` translates rig wiring into that payload and pushes it when
a node appears. It subscribes to `NODE_CAME_ONLINE` rather than being called
directly — `NodeRegistryService` is already a dependency of the zone layer, so a
back-reference would be a cycle. Same reason `RemoteZoneStateService` subscribes to
a new `NODE_APPLIED_STATE_REPORTED` event instead of being called from the registry.

### API

`/nodes/{id}/zones*` is gone. A zone is addressed by **its own id**, because where a
zone renders is a property of the zone, not part of its identity.

```
GET    /v1/rig/catalog
GET    /v1/rig/drivers          PUT/DELETE /v1/rig/drivers/{id}
GET    /v1/rig/fixtures         PUT/DELETE /v1/rig/fixtures/{id}
GET    /v1/rig/zones            GET/PUT/DELETE /v1/rig/zones/{id}
PUT    /v1/rig/zones/{id}/color | brightness | is-on | render-mode
```

`/nodes` keeps heartbeat, listing and command dispatch; `GET /nodes/{id}` now
reports `device_capabilities` derived from what is actually wired to it.

### Frontend

- `FixtureControls` renders **from the capability set** — power / brightness / hue
  picker, else a read-only swatch of the declared physical colour
- `FixturePreview` — live pixels from the existing frame stream
- `FixtureEditForm` — edits label, **physical diode colour**, white profile. First
  piece of the graphical zone add/edit interface
- `RemoteZoneControls` deleted

---

## Verification

| Check | Result |
|---|---|
| Backend tests | **111 passed** (`tests/api tests/services tests/backend tests/domain_models`) |
| Frontend tests | **21 passed**, `npm run type-check` clean |
| Firmware build | clean — RAM 16.4%, Flash 79.4% |
| Pre-existing failures | `tests/engine/*`, `tests/hardware/input/*`, `test_event_bus.py` — confirmed broken **before** this work via `git stash` |

### On real hardware (ESP32 `04:B2:47:9B:BD:E8`, single MOSFET diode on GPIO 23)

- ✅ `GET /v1/rig/zones` reports `["dimming", "switch_binary"]` — **not**
  `addressable_pixels`, **not** `color_control_rgb`
- ✅ `PUT …/color` → **409** with `"Zone 'desk' does not support 'color_control_rgb'"`
- ✅ `PUT …/brightness` → 204, `last_command_delivered: true`
- ✅ Flashed over USB; heartbeats HTTP 200
- ✅ **Automatic config push end-to-end**: backend restart → ESP32 re-resolves via
  mDNS → heartbeat → `NODE_CAME_ONLINE` → `node.config` pushed → serial shows
  `PWM channel 0 (SINGLE) on pin 23` / `Stored output config, version: b1560c5c75d07472`
  — matching the hash computed independently in an isolation test
- ✅ **Restart amnesia fixed**: brightness 55 set before a restart survived it
- ✅ `in_sync: true` after reconciliation

### Not yet verified

- Browser click-through of `/nodes` (no headless browser here)
- Multi-node lockstep (needs a second ESP32)
- Addressable path on real hardware (no strip wired)
- OTA upload

### Cleanup done at the end

- `src/config/esp32_zones.yaml` deleted (confirmed unreferenced first)
- `src/state/rig.json` added to `.gitignore` alongside `state.json`

**Nothing has been committed.** The whole diff is uncommitted, as instructed.

---

## Known issues, recorded and deliberately not fixed

These are real findings from the architecture review, left for the next chapter.
None of them are dead code — the declarative core layer is forward design.

1. **`ZoneID` is a Python enum** → local zones cannot be created at runtime. Hard
   blocker on the graphical zone editor. Remote zones already use free-form strings.
   *And it is not the only enum with this problem.*
2. **Node identity is a MAC address.** `external_node_id` = MAC (stable, meaningful);
   `NodeInstance.id` = a UUID **regenerated every backend restart**, so it is pure
   ceremony and leaks into the API as `instance_id`. MAC is an *address*, not an
   *identity*.
3. **Two classes named `PortDirection`** — `port.py` (str, runtime) and
   `port_definition.py` (auto, declarative).
4. **Two classes named `EventBus`** — `core/` queue router vs `services/` typed
   pub-sub with priority and middleware. A genuine import trap.
5. **`core/event_bus.py`'s `run()` has no try/except** — one `handle_message()`
   raising kills all routing for the process lifetime. `HttpNodeTransport` is
   patched against this; the loop itself is not.
6. **`HostEngine` has no `unregister_node`/`unregister_device`** — nodes, devices,
   ports and connections accumulate forever.
7. **`NodeInstance.node_id` means "node *type* template id"** while `node_id`
   everywhere else means the MAC.
8. **Four event-naming dialects**: `zone.state` / `zones:snapshot` /
   `ZONE_SNAPSHOT_UPDATED` / doc 02's `state:zone:changed`.
9. **No node→host state channel through the graph.**
   `Esp32CommandDevice.state_output_port` exists and nothing publishes to it. The
   heartbeat echo works around this; the reverse transport is still unbuilt.
10. **Two zone models still coexist** — see below.

---

## Part 4 — Direction agreed for the next chapter

Discussed at the end of 2026-09-12. Not implemented, not planned in detail yet.

### Unified zones — agreed

The zones/remote-zones split is wrong and should go. A **zone is a logical group of
things that emit light**; where it renders is a property, and the RPi is just
another node. Zone membership becomes a list of **segments**:

```
Zone "desk"
  ├─ segment  node=rpi5     output=AUX_5V      pixels 0..29
  ├─ segment  node=esp32_A  output=strip       pixels 12..12    ← one single LED
  ├─ segment  node=esp32_B  output=dimmer_ch0  whole fixture
  └─ segment  node=esp32_C  output=strip       pixels 4..9
```

"One LED from five strips on five ESP32s in one zone" is just five segments.

This chapter's rig model is the prerequisite: a segment has to point *at* something,
and driver module + fixture + channel bindings + derived capabilities is that thing.

### The mapping layer — agreed, and it must grow to 2D/3D

`ZoneConfig.start_index` / `end_index` / `reversed` / `gpio` **is** today's mapping
layer — flattened into the zone and hardcoded to 1D. It becomes an explicit
intermediate class, designed from the start to extend to 2D and 3D.

One dimension-agnostic question: *for physical pixel `i` of this segment, what
position in zone space does it read?* 1D is a 1-tuple, 2D a pair, 3D a triple —
same code path, which is what makes it grow rather than fork.

| Mapping | Dim | Replaces / enables |
|---|---|---|
| `LinearRun(offset, count, reverse)` | 1 | exactly today's `start_index`/`end_index`/`reversed` |
| `SerpentineGrid(origin, w, h, start_corner)` | 2 | the `MATRIX` zone — 48 px currently pretending to be a line |
| `GridRun` (row-major) | 2 | panels |
| `ExplicitPositions([...])` | 2/3 | photo-mapping / calibrated placement |
| `Transform(inner, translate, rotate, scale)` | any | placing a panel in a room |

Recommended: normalized (0..1) coordinates at the mapping boundary, canvas at native
resolution. Absolute integer indices re-bake resolution into every consumer — the
exact mistake `start_index`/`pixel_count` already made.

Nothing downstream currently assumes >1D in a way that blocks this:
`OutputFrame.zones` is a flat `List[Color]` per zone, which is correct — physical
pixels *are* flat per segment; the canvas is the N-dimensional thing.
`CompactLEDPreview` is flat and will need a grid sibling later.

### Frame distribution — corrected terminology

There is **no "sink" concept and none should be invented.** What exists is a
**published frame stream**; whoever registers on that channel receives frames. A
subscriber may be a node, a hook, or something virtual. `FrameManager` already
fans out to `led_channels` *and* to the stream — that is the existing pattern, and
it is the one to formalise.

### Animations as portable contracts — future direction

- Animations become **functions with contracts**, likely defined in a protocol
  language rather than Python classes.
- **Renderers become separate implementations.** A frontend renderer will *try* to
  reproduce what an ESP32 renderer does; exact parity is explicitly **not** expected,
  differences are accepted.
- ESP32s receive animation commands **with a time delay** — told what to display in
  ~3 seconds — so each node knows what to animate ahead of time and starts in step.
  The NTP + multicast phase reference from Phase 7 is the groundwork for this.

This supersedes the earlier framing of "port each animation to C++". The contract is
the shared artefact; each renderer implements it as well as it can.

### Sequencing agreed

1. Finish and stabilise the current rig work *(done — this document)*
2. **Then a fresh brainstorm session** on the enum problem — `ZoneID` needs to change
   ASAP, but it is not the only enum with this constraint, so the whole set gets
   looked at together rather than one at a time
3. Unified zone + segment + mapping model
4. Node identity UUIDs (MAC demoted to a discovery key)
