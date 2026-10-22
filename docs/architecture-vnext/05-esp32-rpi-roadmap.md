# ESP32 <-> RPi5 Roadmap v1 (Current)

## Status

**Phase 1 (Basic reachability): DONE**

- Backend: `src/api/routes/nodes.py` - in-memory node registry, standalone (not wired into `HostEngine`/`ServiceContainer` yet)
  - `POST /api/v1/nodes/heartbeat` - node reports `{node_id, node_type, address, firmware}`
  - `GET /api/v1/nodes` - lists known nodes with computed `online` flag (last_seen within 15s)
- Firmware: `firmware/firmware/src/main.cpp` - ESP32 connects to WiFi, POSTs a heartbeat every 5s, runs the MOSFET breathing animation via a non-blocking `millis()` state machine (no more blocking `delay()` loops)
- Credentials: `firmware/firmware/include/secrets.h` (gitignored, template at `secrets.h.example`)
- Verified end-to-end: ESP32 heartbeat visible in the RPi5's live `/api/v1/nodes` response

Full detail: see the approved plan this phase came from (`i-have-three-working-merry-dolphin` plan) and `.claude/context/.todo/2026.01.14/ESP32_RPi4_Cooperation_Guide.md` for the original transport/architecture research.

**Phase 2 (Harden the link): DONE**

- ESP32: `firmware/firmware/src/main.cpp` - WiFi connect/reconnect is now a non-blocking `millis()` state machine (`updateWifiConnection()`, mirrors the breathe animation's pattern). `setup()` no longer blocks forever on first connect; a dropped or failed connection retries every `WIFI_RECONNECT_RETRY_INTERVAL_MILLISECONDS` (5s) after a `WIFI_CONNECT_TIMEOUT_MILLISECONDS` (15s) timeout
- RPi5: `src/api/routes/nodes.py` - background `asyncio` watchdog task (`start_node_watchdog`/`stop_node_watchdog`, wired into `api/main.py`'s lifespan) polls every 5s and publishes `NodeWentOfflineEvent`/`NodeCameOnlineEvent` (`src/models/events/node_events.py`) on the shared `EventBus.instance()` singleton on actual state transitions, not just a computed flag on `GET /nodes` read
- Basic auth: `/api/v1/nodes/heartbeat` now requires an `X-Node-Secret` header matching `DIUNA_NODE_SHARED_SECRET` (backend env var, insecure dev default with a startup warning if unset) / `NODE_SHARED_SECRET` (firmware `secrets.h`); rejects with 401 otherwise
- Verified: firmware builds clean (`pio run`); backend heartbeat auth (401 on missing/wrong secret, 200 with correct secret) and watchdog online/offline event transitions confirmed against a live local server

**Phase 3 (Discovery): DONE**

- ESP32: `firmware/firmware/src/main.cpp` - `RPI_HOST` (hardcoded IP) is gone. On WiFi connect, `beginMdnsIfNeeded()` starts an mDNS responder under a per-device hostname (`diuna-esp32-<mac suffix>`, avoids collisions between multiple nodes), then `resolveRpiAddress()` queries `RPI_MDNS_HOSTNAME` (secrets.h, e.g. the Pi's default `raspberrypi` hostname - resolved via the avahi-daemon that ships with Raspberry Pi OS, no backend changes needed) and caches the returned IP
- Self-healing: a transport-level heartbeat failure (`responseCode <= 0`) or a WiFi drop invalidates the cached address, and `updateRpiDiscovery()` retries the mDNS lookup every `RPI_DISCOVERY_RETRY_INTERVAL_MILLISECONDS` (10s) until it succeeds - so a Pi reboot that changes its DHCP lease no longer needs a reflash
- Config: `secrets.h`/`secrets.h.example` - `RPI_HOST` replaced with `RPI_MDNS_HOSTNAME` (bare hostname, no `.local` suffix, no port)
- Verified: firmware builds clean (`pio run`) with `ESPmDNS` linked in
- Not yet field-tested against a real Pi's avahi responder end-to-end (only compiled) - worth confirming `RPI_MDNS_HOSTNAME` in `secrets.h` matches the Pi's actual `hostname -s` before relying on it

**Phase 4 (Real commands, RPi5 -> ESP32): DONE**

- Backend: `src/backend/core/http_node_transport.py` - concrete `HttpNodeTransport` implementing the `NodeTransport` Protocol under `TransportProtocol.WEB_API`; POSTs `{name, payload}` to `http://<node address>:<command_port>/command`. Deliberately swallows delivery failures (logs and returns) rather than raising, since it runs inside `HostEngine`'s single shared consumer loop (`core/event_bus.py`'s `run()`, no try/except of its own) - letting one unreachable node's exception escape killed command delivery to *every* node for the rest of the process's life (caught live while building this phase, see `tests/backend/core/test_http_node_transport.py`)
- Backend: `src/backend/core/esp32_command_device.py` (`Esp32CommandDevice`, addressable per-node command endpoint) and `src/backend/core/node_command_router_device.py` (`NodeCommandRouterDevice`, one dedicated output port per node so commands don't fan out to every node)
- Backend: `src/services/node_registry_service.py` - `NodeRegistryService` owns a `HostEngine` instance, folds the old standalone dict registry into it (MAC string -> stable `NodeInstance` UUID), runs the watchdog, and exposes `send_command()`. NodeInstance must be `register_node()`-ed *before* `register_device()` for a new node - `register_device()` raises if its node isn't already in `HostEngine.nodes`
- Backend: `src/api/routes/nodes.py` rewritten on top of `NodeRegistryService` (`GET/POST /nodes`, `GET /nodes/{id}`, `POST /nodes/{id}/command`); `src/api/main.py`'s lifespan now starts/stops the registry's watchdog and closes its transport
- Backend: `src/main_asyncio.py`/`src/services/service_container.py` wire `NodeRegistryService` in; its `HostEngine` message loop runs as a tracked background task, cancelled automatically by the existing `AllTasksCancellationHandler` safety net on shutdown (no separate wiring needed)
- Firmware: `firmware/firmware/src/main.cpp` - `WebServer` command endpoint (`/command`, port `NODE_COMMAND_PORT`) handling `identify` (2s LED blink, the first physically-observable "RPi sends a real command" milestone) and `zone.state` (Phase 6); heartbeat payload now includes `command_port` and `capabilities`
- Verified: 47 new backend tests pass (`pytest tests/backend/core tests/domain_models tests/services tests/api`); live-tested against the running app with real heartbeats/commands/shutdown cycles, including a real physical ESP32 already on the LAN sending old-format heartbeats (handled gracefully via Pydantic defaults)
- Not yet field-tested: the `/command` WebServer itself (firmware compiles by inspection only - no `pio run` available in the dev sandbox this was built in, and the deployed ESP32 needs reflashing to pick this up)

**Phase 5 (Capabilities model): DONE**

- Backend: `src/backend/core/capabilities.py` - `NODE_CAPABILITIES`/`DEVICE_CAPABILITIES` vocabulary (mirrors `04-capabilities.md`), `ESP32_LED_STRIP_DEVICE_CAPABILITIES`, `split_known_node_capabilities()` (filters unknown capabilities out of a heartbeat, logs a warning, doesn't hard-fail)
- Backend: `NodeRegistryService.register_or_update_node()` validates heartbeat capabilities against the vocabulary; `GET /api/v1/nodes/{node_id}` reports both node-level (dynamic, from heartbeat) and `declared_device_capabilities` (static, from `ESP32_LED_STRIP_DEVICE_CAPABILITIES` for ESP32 nodes)
- Verified: `tests/backend/core/test_capabilities.py`, `tests/api/test_nodes_routes.py::test_get_node_includes_declared_device_capabilities`

**Phase 6 (Real addressable LEDs on ESP32, stream state not frames): DONE**

- Architecture: remote zones are a deliberately separate, additive pipeline from the local-GPIO `ZoneID`/`ZoneService`/`FrameManager` stack - they don't touch `zones.yaml`/`zone_mapping.yaml`/`HardwareManager`, since an ESP32-driven strip renders on the ESP32 itself, not the RPi
- Backend: `src/models/domain/remote_zone.py` (`RemoteZoneConfig`, `RemoteZoneState`, `load_remote_zone_configs()`), `src/config/esp32_zones.yaml` (independent YAML, not merged through `ConfigManager`'s include system)
- Backend: `src/services/remote_zone_render_bridge.py` - `RemoteZoneRenderBridge` owns per-zone state and pushes `zone.state` commands (`is_on`, `brightness`, `color: {r,g,b}`, `render_mode`) through `NodeRegistryService.send_command()` on every mutation
- Backend: `src/api/routes/nodes.py` - `GET /nodes/{id}/zones`, `PUT /nodes/{id}/zones/{label}/color|brightness|is-on`
- Firmware: `firmware/firmware/src/main.cpp` - MOSFET PWM code fully replaced with `FastLED`/WS2812B (`firmware/firmware/include/led_config.h` for pin/pixel-count); `zone.state` command applies color/brightness/on-off; `render_mode: "BREATHE"` keeps the built-in breathe animation, now driving the real strip
- Verified: 9 new backend tests pass; live-tested `PUT .../color` and `.../brightness` against the running app (`RemoteZoneRenderBridge` correctly enqueues and the state read-back reflects the change)
- Not yet field-tested: FastLED strip rendering itself (needs a real WS2812B strip wired to `LED_STRIP_DATA_PIN` and a reflash)

**Phase 7 (Multi-node sync): DONE**

- Scoped narrowly per this doc's own "only if needed"/"heavyweight" note: phase-sync for the existing built-in BREATHE animation only, not a generic parameter-sync system
- Backend: `src/services/multi_node_sync_broadcaster.py` - `MultiNodeSyncBroadcaster` computes `sync_group` membership from `RemoteZoneRenderBridge.list_zones()` + `NodeRegistryService.get_node()` (online nodes only), multicasts `{sync_group, reference_epoch_ms, cycle_duration_ms}` to `239.255.10.10:41234` every 2s whenever a group has >=2 online members
- Firmware: `firmware/firmware/src/main.cpp` - NTP sync (`configTime`) + `WiFiUdp` multicast listener (`NODE_SYNC_GROUP` in `secrets.h` must match the zone's `sync_group`); `updateBreatheAnimation()` prefers a synced triangle-wave phase (driven by wall-clock time) over the local `millis()` state machine once a reference is known, falling back to the old per-device animation otherwise
- Verified: 3 new backend tests pass (`tests/services/test_multi_node_sync_broadcaster.py`)
- Not yet field-tested: actual multi-device lockstep (needs >=2 real ESP32s with strips, sharing a `sync_group`)

**Phase 8 (Production hardening): DONE**

- Frontend: `frontend/src/api/socketio/nodes/broadcaster.py` equivalent on the frontend side - see the new Nodes page below; Socket.IO `nodes:snapshot`/`node:snapshot` events broadcast live (`src/api/socketio/nodes/broadcaster.py`, wired in `on_connect.py`/`registry.py`)
- Firmware: `firmware/firmware/src/main.cpp` - `ArduinoOTA` wireless updates (hostname matches the mDNS name), started alongside mDNS on each successful WiFi connection
- Deployment: `deploy/diuna-backend.service` (systemd unit) + `deploy/README.md` (install steps)
- Not yet field-tested: OTA upload itself (needs a real device already running this firmware over WiFi)

## Frontend: Nodes page

- New top-level `/nodes` route (`frontend/src/pages/Nodes.tsx`, nav entry in `MainLayout.tsx`) showing every connected node's connection properties (address, firmware, capability badges, online/offline, last-seen) and an "Identify" button exercising Phase 4's command endpoint
- `frontend/src/features/nodes/` mirrors the existing `features/zones` realtime pattern exactly: `useSyncExternalStore`-based store (`realtime/nodes.store.ts`) + a Socket.IO side-effect module (`realtime/nodes.socket.ts`) imported once in `main.tsx`
- Expandable per-node remote zone controls (`RemoteZoneControls.tsx`) for Phase 6 zones - color (via the existing `HueColorPicker`), brightness, power - reusing `shared/ui/power-switch.tsx` and `shared/ui/slider.tsx`
- Verified: 13 new frontend tests pass (`npm test`), first tests of any kind in the frontend codebase - along the way, fixed two pre-existing test-infra gaps that had never been exercised: `vitest.config.ts`'s empty `setupFiles` (meant `@testing-library/jest-dom` matchers never worked) and jsdom's missing `ResizeObserver` (needed by the canvas-based `HueWheelPicker`). Both fixed in `frontend/src/test/setup.ts`
- `npm run type-check` clean; dev server serves `/nodes` and all existing routes without module-resolution errors
- Not yet visually verified in an actual browser (no headless browser tool available in this environment) - the dev-server module graph, TypeScript compilation, and jsdom-rendered component tests all pass, but a real click-through hasn't been done
