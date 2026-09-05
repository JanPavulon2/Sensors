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

## Phase 4 - Real commands (RPi5 -> ESP32)

- Today the RPi5 only *hears from* the ESP32. Next: RPi5 *sends* commands.
- This is what `src/backend/core/node_transport.py` (`TransportProtocol`, `NodeTransport` Protocol) and `HostEngine._deliver()` were already built for - implement a concrete HTTP-based `NodeTransport`, register the ESP32 as a real `NodeInstance`, wire `HostEngine` into `main_asyncio.py`/`ServiceContainer`
- Fold today's standalone `nodes.py` registry into that model at this point (not before - the shape wasn't proven until Phase 1 worked)

## Phase 5 - Capabilities model

- Use the vocabulary already defined in `04-capabilities.md` ("ESP32 node -> LED strip" example: node capabilities `render_output`, `command_execution`, `telemetry_publish`; device capabilities `addressable_pixels`, `color_control_rgb`)
- Each node reports its capabilities on registration so the Host knows what it can/can't command - required once there's more than one ESP32 with different hardware

## Phase 6 - Real addressable LEDs on ESP32

- Firmware currently drives a single MOSFET-dimmed LED. Swap to FastLED + WS281x once an actual strip is attached
- Switch from "RPi tells ESP32 to breathe" to "RPi streams zone state, ESP32 renders it locally" - the cooperation guide's "stream state, not frames" verdict

## Phase 7 - Multi-node sync (only if needed)

- NTP time sync + UDP multicast state broadcast (detailed in the cooperation guide) for multiple physically-separate ESP32 fixtures that must stay visually in lockstep
- Heavyweight - only worth building once there are >=2 ESP32s that actually need synchronized rendering

## Phase 8 - Production hardening

- Frontend: `devices` Socket.IO broadcaster mirroring `zones/broadcaster.py`, so the React UI shows connected nodes live
- OTA firmware updates instead of USB flashing
- systemd service for the RPi backend (see `.claude/context/verdent/DIUNA_VISION_AND_ROADMAP.md` for a starting unit file)
