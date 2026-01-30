# 🔌 ESP32 + Raspberry Pi 4 Cooperation Guide
## A Comprehensive Architecture for Distributed LED Control Systems

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Communication Methods Overview](#communication-methods-overview)
3. [Physical Connections (Wired)](#physical-connections-wired)
4. [Wireless Connections](#wireless-connections)
5. [Protocol Deep Dives](#protocol-deep-dives)
6. [Architecture Patterns](#architecture-patterns)
7. [The Synchronization Problem](#the-synchronization-problem)
8. [Frame Streaming vs State Streaming](#frame-streaming-vs-state-streaming)
9. [Practical Recommendations for Diuna](#practical-recommendations-for-diuna)
10. [ESP32 Project Ideas](#esp32-project-ideas)
11. [Implementation Examples](#implementation-examples)

---

## Executive Summary

### The Core Question

You have two powerful but different devices:

| Device | Strengths | Weaknesses |
|--------|-----------|------------|
| **Raspberry Pi 4** | Powerful CPU, runs Python/Linux, complex calculations, networking stack, storage | Higher power consumption, no real-time guarantees, slower GPIO |
| **ESP32** | Real-time capable, ultra-fast GPIO, low power, WiFi/BLE built-in, dual-core | Limited RAM (520KB), no OS overhead but also no OS benefits |

**The fundamental question:** Who calculates what, and how do they talk?

### Quick Answer for Your Use Case

For LED animation systems, I recommend a **hybrid architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     RECOMMENDED ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         WiFi/UDP          ┌─────────────┐     │
│  │             │  ───────────────────────▶ │             │     │
│  │   RPi 4     │   Animation State +       │   ESP32     │     │
│  │  (Brain)    │   Sync Timestamps         │  (Muscle)   │     │
│  │             │  ◀─────────────────────── │             │     │
│  └─────────────┘      Status/Sensors       └─────────────┘     │
│                                                                 │
│  • Runs Diuna backend                   • Receives state        │
│  • Calculates animations                • Renders frames locally│
│  • Serves Web UI                        • Drives WS2812 strips  │
│  • Stores presets/config                • Handles precise timing│
│  • Complex math/AI                      • Sensors/buttons       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight:** Don't stream frames. Stream *animation state* with timestamps. Let ESP32 render locally.

---

## Communication Methods Overview

### Comparison Matrix

| Method | Speed | Range | Complexity | Latency | Best For |
|--------|-------|-------|------------|---------|----------|
| **UART** | 115200-921600 bps | 1-2m | Low | <1ms | Simple commands, debugging |
| **SPI** | Up to 80 MHz | 10-20cm | Medium | <0.1ms | High-speed bulk data |
| **I2C** | 100-400 kHz | 1m | Medium | ~1ms | Multiple sensors, config |
| **WiFi TCP** | 10+ Mbps | 50m+ | High | 5-50ms | Reliable data, API calls |
| **WiFi UDP** | 10+ Mbps | 50m+ | Medium | 1-10ms | Real-time streaming |
| **ESP-NOW** | 1 Mbps | 200m+ | Low | <1ms | Fast P2P, no router needed |
| **MQTT** | Varies | Network | Medium | 10-100ms | IoT, pub/sub, home automation |
| **WebSocket** | 10+ Mbps | Network | High | 5-20ms | Bidirectional, web integration |
| **BLE** | 1-2 Mbps | 10-30m | High | 10-100ms | Mobile apps, low power |

### Decision Tree

```
                        ┌─────────────────────┐
                        │ Do you need WiFi    │
                        │ range (>2 meters)?  │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                   YES                           NO
                    │                             │
            ┌───────▼───────┐             ┌──────▼──────┐
            │ Need router   │             │ Need high   │
            │ infrastructure?│             │ speed (>1MB)?│
            └───────┬───────┘             └──────┬──────┘
                    │                             │
         ┌──────────┴──────────┐      ┌──────────┴──────────┐
         │                     │      │                     │
        YES                   NO     YES                   NO
         │                     │      │                     │
    ┌────▼────┐          ┌────▼────┐ ┌────▼────┐      ┌────▼────┐
    │WiFi TCP │          │ESP-NOW  │ │  SPI    │      │  UART   │
    │WiFi UDP │          │(P2P)    │ │         │      │  I2C    │
    │MQTT     │          │         │ │         │      │         │
    └─────────┘          └─────────┘ └─────────┘      └─────────┘
```

---

## Physical Connections (Wired)

### 1. UART (Serial)

**What it is:** Simple two-wire (TX/RX) serial communication.

**Wiring:**
```
RPi 4                           ESP32
┌─────────────┐                ┌─────────────┐
│ GPIO 14 (TX)│───────────────▶│ GPIO 16 (RX)│
│ GPIO 15 (RX)│◀───────────────│ GPIO 17 (TX)│
│ GND         │────────────────│ GND         │
└─────────────┘                └─────────────┘

⚠️ IMPORTANT: RPi uses 3.3V logic, ESP32 uses 3.3V - SAFE to connect directly!
   (Unlike Arduino which uses 5V and needs level shifter)
```

**Speeds:**
- Standard: 115200 bps (~14 KB/s)
- High-speed: 921600 bps (~112 KB/s)
- Maximum practical: ~2 Mbps with good wiring

**Pros:**
- Dead simple
- Low latency (<1ms)
- Works everywhere
- Easy to debug (just print text)

**Cons:**
- Slow for frame data (100 LEDs × 3 bytes × 60 FPS = 18 KB/s minimum)
- Point-to-point only (one ESP32 per UART)
- Cable length limited (~2m)

**Best for:**
- Command/response protocols
- Configuration updates
- Debugging
- Low LED count systems

**Example Protocol:**
```
# Simple command format
CMD:SET_HUE:180\n
CMD:SET_BRIGHTNESS:200\n
CMD:START_ANIM:RAINBOW:1.5\n
ACK:OK\n
```

---

### 2. SPI (Serial Peripheral Interface)

**What it is:** High-speed synchronous 4-wire protocol. Master (RPi) controls clock.

**Wiring:**
```
RPi 4                           ESP32
┌─────────────┐                ┌─────────────┐
│ GPIO 10 MOSI│───────────────▶│ GPIO 23 MOSI│  (Master Out, Slave In)
│ GPIO 9  MISO│◀───────────────│ GPIO 19 MISO│  (Master In, Slave Out)
│ GPIO 11 SCLK│───────────────▶│ GPIO 18 SCLK│  (Clock)
│ GPIO 8  CE0 │───────────────▶│ GPIO 5  SS  │  (Chip Select)
│ GND         │────────────────│ GND         │
└─────────────┘                └─────────────┘
```

**Speeds:**
- ESP32 SPI slave: Up to 10 MHz reliable
- Theoretical: 80 MHz (but not as slave)
- Practical throughput: 1-5 MB/s

**Pros:**
- Very fast (could stream raw frames)
- Deterministic timing (clock-synchronized)
- Multiple devices possible (separate CS lines)

**Cons:**
- More wires (4 minimum)
- Short cable length (<30cm ideal)
- RPi SPI slave mode is problematic (better as master)
- More complex setup

**Best for:**
- High-bandwidth local connections
- Frame streaming (if wired is acceptable)
- Display panels, matrix controllers

**Frame Streaming Example:**
```python
# RPi sends frame over SPI
import spidev

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 8000000  # 8 MHz

def send_frame(pixels: List[Tuple[int, int, int]]):
    # Header: [0xAA, 0x55, num_pixels_high, num_pixels_low]
    header = [0xAA, 0x55, len(pixels) >> 8, len(pixels) & 0xFF]
    data = header + [c for p in pixels for c in p]  # Flatten RGB
    spi.xfer2(data)
```

---

### 3. I2C (Inter-Integrated Circuit)

**What it is:** Two-wire bus protocol with addressing. Multiple devices share same bus.

**Wiring:**
```
RPi 4                           ESP32
┌─────────────┐                ┌─────────────┐
│ GPIO 2 (SDA)│◀──────────────▶│ GPIO 21 SDA │  (Data - bidirectional)
│ GPIO 3 (SCL)│───────────────▶│ GPIO 22 SCL │  (Clock)
│ GND         │────────────────│ GND         │
└─────────────┘                └─────────────┘
                    │
                    │         ┌─────────────┐
                    └────────▶│ More ESP32s │  (Different addresses)
                              │ or sensors  │
                              └─────────────┘

⚠️ Requires 4.7kΩ pull-up resistors on SDA and SCL to 3.3V
```

**Speeds:**
- Standard: 100 kHz (~12.5 KB/s)
- Fast: 400 kHz (~50 KB/s)
- Fast Plus: 1 MHz (~125 KB/s)

**Pros:**
- Only 2 wires for multiple devices
- Addressable (up to 127 devices)
- Built-in acknowledgment
- Great for configuration

**Cons:**
- Slow for streaming
- Bus contention possible
- Pull-up resistors needed
- Limited cable length (~1m)

**Best for:**
- Multi-ESP32 setups with shared config
- Sensor networks
- EEPROM/configuration storage
- NOT for frame streaming

---

## Wireless Connections

### 4. WiFi TCP (Reliable)

**What it is:** Standard TCP/IP over WiFi. Guaranteed delivery, ordered packets.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                         WiFi Network                         │
│                                                             │
│  ┌─────────┐         ┌─────────┐         ┌─────────┐       │
│  │  RPi 4  │◀───────▶│ Router  │◀───────▶│  ESP32  │       │
│  │ Server  │   TCP   │         │   TCP   │ Client  │       │
│  └─────────┘         └─────────┘         └─────────┘       │
│  192.168.1.10        192.168.1.1         192.168.1.20      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Guaranteed delivery (retransmission)
- Ordered packets
- Works through standard infrastructure
- Easy debugging (Wireshark, curl)
- Firewall-friendly

**Cons:**
- Higher latency (TCP handshake, ACKs)
- Head-of-line blocking (one lost packet stalls stream)
- More overhead
- Variable latency (bad for real-time)

**Best for:**
- Configuration updates
- REST API calls
- File transfers
- Non-real-time commands

---

### 5. WiFi UDP (Fast)

**What it is:** Connectionless UDP over WiFi. No guarantees, but fast.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                         WiFi Network                         │
│                                                             │
│  ┌─────────┐    UDP Datagrams (fire & forget)  ┌─────────┐ │
│  │  RPi 4  │─────────────────────────────────▶│  ESP32  │  │
│  │ Sender  │         No acknowledgment         │ Receiver│  │
│  └─────────┘                                   └─────────┘  │
│                                                             │
│  Can also broadcast to multiple ESP32s simultaneously!      │
│  └──────▶ 192.168.1.255 (broadcast)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Low latency (no ACKs, no connection)
- Can broadcast/multicast to many ESP32s
- Simple implementation
- Good for real-time data (lost frames = skip, don't wait)

**Cons:**
- No delivery guarantee
- Packets can arrive out of order
- No congestion control
- Need to handle packet loss yourself

**Best for:**
- Real-time state streaming
- Broadcast to multiple ESP32s
- Sensor data (latest value matters, not all values)

**Frame Streaming Protocol (UDP):**
```python
# RPi sender
import socket
import struct
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ESP32_IP = "192.168.1.20"
PORT = 5000

def send_state(animation_id: int, params: dict, timestamp: float):
    """Send animation state, not frames"""
    # Packet format:
    # [4 bytes: timestamp][1 byte: anim_id][variable: params]
    packet = struct.pack(
        ">fB",  # Big-endian: float timestamp, unsigned byte anim_id
        timestamp,
        animation_id
    )
    # Add params as JSON or binary
    packet += json.dumps(params).encode()
    sock.sendto(packet, (ESP32_IP, PORT))
```

---

### 6. ESP-NOW (Peer-to-Peer)

**What it is:** Espressif's proprietary P2P protocol. No router needed!

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    ESP-NOW Network                           │
│                    (No router needed!)                       │
│                                                             │
│  ┌─────────┐         Direct Link         ┌─────────┐       │
│  │  ESP32  │◀═══════════════════════════▶│  ESP32  │       │
│  │ Master  │      250 bytes/packet       │  Slave  │       │
│  └─────────┘        ~1ms latency         └─────────┘       │
│       │                                                     │
│       │             ┌─────────┐                             │
│       └════════════▶│  ESP32  │  Can have up to 20 peers   │
│                     │  Slave  │                             │
│                     └─────────┘                             │
│                                                             │
│  ⚠️ Problem: RPi doesn't natively support ESP-NOW!          │
│     Solution: Use ESP32 as bridge (USB/Serial to RPi)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**RPi Integration Pattern:**
```
┌─────────┐  UART   ┌─────────┐  ESP-NOW  ┌─────────┐
│  RPi 4  │────────▶│ ESP32   │══════════▶│ ESP32   │
│ (Brain) │         │ Bridge  │           │ (LEDs)  │
└─────────┘         └─────────┘           └─────────┘
                                          ┌─────────┐
                                    ═════▶│ ESP32   │
                                          │ (LEDs)  │
                                          └─────────┘
```

**Pros:**
- Ultra-low latency (<1ms)
- No router infrastructure needed
- Works even when WiFi network is down
- Long range (200m+ open air)
- Broadcast to 20 peers
- Encrypted option available

**Cons:**
- ESP32 only (RPi needs bridge ESP32)
- 250 bytes max per packet
- No routing (flat topology)
- Espressif proprietary

**Best for:**
- Wearables (no WiFi available)
- Multi-ESP32 synchronized systems
- Low-latency requirements
- Portable installations

---

### 7. MQTT (Message Queue)

**What it is:** Publish/subscribe protocol designed for IoT. Uses broker.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                       MQTT Network                           │
│                                                             │
│                    ┌─────────────┐                          │
│                    │ MQTT Broker │  (Mosquitto on RPi)      │
│                    │ RPi or Cloud│                          │
│                    └──────┬──────┘                          │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐          │
│    │  RPi 4  │      │  ESP32  │      │  ESP32  │          │
│    │Publisher│      │Subscriber│      │Subscriber│          │
│    └─────────┘      └─────────┘      └─────────┘          │
│                                                             │
│  Topics:                                                    │
│  • diuna/zones/floor/color   → {hue: 180, sat: 100}        │
│  • diuna/animations/active   → {id: "rainbow", speed: 1.5} │
│  • diuna/sync/timestamp      → {time: 1234567890.123}      │
│  • diuna/esp32/status/#      → Wildcards!                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Pub/sub is perfect for distributed systems
- Retained messages (ESP32 gets latest on connect)
- QoS levels (0=fire-forget, 1=at-least-once, 2=exactly-once)
- Wildcards (subscribe to diuna/# for all)
- Last Will (detect disconnects)
- Great tooling (MQTT Explorer, mosquitto_sub)

**Cons:**
- Needs broker (additional service)
- Higher latency than UDP (~10-100ms)
- More overhead than raw UDP
- QoS 2 adds significant latency

**Best for:**
- Home automation integration
- State synchronization across many devices
- Resilient systems (retained messages)
- When you need message guarantees

**Topic Design for Diuna:**
```
diuna/
├── zones/
│   ├── floor/
│   │   ├── color     → {"hue": 180, "sat": 100, "bright": 255}
│   │   └── state     → {"enabled": true, "mode": "static"}
│   └── lamp/
│       ├── color
│       └── state
├── animations/
│   ├── active        → {"id": "rainbow", "params": {...}}
│   └── library/      → Available animations list
├── sync/
│   ├── clock         → {"timestamp": 1234567890.123}
│   └── heartbeat     → {"esp32_id": "wearable_1", "uptime": 3600}
└── config/
    └── esp32/
        └── {device_id}/  → Per-device configuration
```

---

### 8. WebSocket (Bidirectional Web)

**What it is:** Full-duplex communication over HTTP upgrade. Perfect for web integration.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Architecture                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    RPi 4 (Server)                    │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │              FastAPI + WebSocket              │    │   │
│  │  │                                               │    │   │
│  │  │  ws://192.168.1.10:8000/ws/led_state         │    │   │
│  │  │  ws://192.168.1.10:8000/ws/sync              │    │   │
│  │  └───────────────────┬───────────────────────────┘    │   │
│  └──────────────────────┼────────────────────────────────┘   │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         │               │               │                   │
│    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐              │
│    │ Browser │    │  ESP32  │    │  ESP32  │              │
│    │ (React) │    │(WS Client)│   │(WS Client)│              │
│    └─────────┘    └─────────┘    └─────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Bidirectional (server can push to client)
- Works through HTTP proxies
- Same connection for web UI and ESP32
- JSON-friendly
- Built into browsers

**Cons:**
- Higher overhead than raw UDP
- TCP underneath (same issues)
- More complex than UDP
- Reconnection logic needed

**Best for:**
- When you already have web UI (your case!)
- Unified API for browser + ESP32
- When you need bidirectional (ESP32 sends sensor data back)

---

## Protocol Deep Dives

### Socket.IO (Your Mentioned Technology)

**What it is:** Real-time library on top of WebSocket with fallbacks.

**Features:**
- Auto-reconnection
- Room support (broadcast to subset)
- Acknowledgments
- Binary support
- Fallback to HTTP long-polling

**ESP32 Support:**
- Library: `arduinoWebSockets` or `SocketIOclient`
- Works, but adds overhead
- Consider raw WebSocket for ESP32, Socket.IO for browser

**Example (Python Server):**
```python
from fastapi import FastAPI
from fastapi_socketio import SocketManager

app = FastAPI()
socket_manager = SocketManager(app=app)

@app.sio.on('connect')
async def handle_connect(sid, environ):
    print(f"Client connected: {sid}")

@app.sio.on('get_state')
async def handle_get_state(sid):
    return await get_current_led_state()

async def broadcast_state_change(state):
    await app.sio.emit('state_changed', state)
```

**Example (ESP32 Client):**
```cpp
#include <SocketIOclient.h>

SocketIOclient socketIO;

void socketIOEvent(socketIOmessageType_t type, uint8_t* payload, size_t length) {
    switch(type) {
        case sIOtype_EVENT:
            // Parse JSON event
            handleEvent(payload, length);
            break;
    }
}

void setup() {
    socketIO.begin("192.168.1.10", 8000, "/socket.io/?EIO=4");
    socketIO.onEvent(socketIOEvent);
}

void loop() {
    socketIO.loop();
}
```

---

## Architecture Patterns

### Pattern 1: Centralized (RPi Does Everything)

```
┌─────────────────────────────────────────────────────────────┐
│                  CENTRALIZED ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────┐               │
│  │              RPi 4 (Master)              │               │
│  │                                          │               │
│  │  • Runs Diuna backend                    │               │
│  │  • Calculates ALL animation frames       │               │
│  │  • Sends raw pixel data to ESP32s        │               │
│  │  • Handles all user input                │               │
│  │  • Stores all state                      │               │
│  └─────────────────────┬────────────────────┘               │
│                        │                                    │
│                        │ Frame data (RGB arrays)            │
│                        │ @ 60 FPS                           │
│                        │                                    │
│         ┌──────────────┼──────────────┐                    │
│         ▼              ▼              ▼                    │
│    ┌─────────┐   ┌─────────┐   ┌─────────┐               │
│    │ ESP32   │   │ ESP32   │   │ ESP32   │               │
│    │ "Dumb"  │   │ "Dumb"  │   │ "Dumb"  │               │
│    │ Driver  │   │ Driver  │   │ Driver  │               │
│    └────┬────┘   └────┬────┘   └────┬────┘               │
│         │             │             │                      │
│    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐               │
│    │ LEDs    │   │ LEDs    │   │ LEDs    │               │
│    │ Zone 1  │   │ Zone 2  │   │ Zone 3  │               │
│    └─────────┘   └─────────┘   └─────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Data Flow:
RPi calculates: [R,G,B, R,G,B, R,G,B, ...] for each frame
Sends via: UDP/SPI at 60 FPS
ESP32 receives: Raw bytes, writes to WS2812, done.

Bandwidth Required (per ESP32):
• 100 LEDs × 3 bytes × 60 FPS = 18 KB/s
• 500 LEDs × 3 bytes × 60 FPS = 90 KB/s
• 1000 LEDs × 3 bytes × 60 FPS = 180 KB/s
```

**Pros:**
- Simple ESP32 code (just receive and display)
- All logic in Python (easier to develop)
- Perfect synchronization (RPi controls timing)
- Easy to add new animations (only change RPi code)

**Cons:**
- High bandwidth requirement
- Network latency causes visible jitter
- Single point of failure (RPi down = all dark)
- WiFi packet loss = visual glitches
- ESP32 capabilities wasted

**When to Use:**
- Low LED counts (<100 per ESP32)
- Wired connection (SPI/UART)
- When animations require complex calculations
- Prototyping phase

---

### Pattern 2: Distributed (ESP32 Calculates Locally)

```
┌─────────────────────────────────────────────────────────────┐
│                 DISTRIBUTED ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────┐               │
│  │              RPi 4 (Coordinator)         │               │
│  │                                          │               │
│  │  • Runs Diuna backend + Web UI           │               │
│  │  • Sends animation STATE, not frames     │               │
│  │  • Broadcasts sync timestamps            │               │
│  │  • Stores presets/config                 │               │
│  │  • Handles user input                    │               │
│  └─────────────────────┬────────────────────┘               │
│                        │                                    │
│                        │ State messages (small)             │
│                        │ {anim: "rainbow", speed: 1.5,      │
│                        │  timestamp: 1234567.890}           │
│                        │                                    │
│         ┌──────────────┼──────────────┐                    │
│         ▼              ▼              ▼                    │
│    ┌─────────┐   ┌─────────┐   ┌─────────┐               │
│    │ ESP32   │   │ ESP32   │   │ ESP32   │               │
│    │ "Smart" │   │ "Smart" │   │ "Smart" │               │
│    │ Has own │   │ Has own │   │ Has own │               │
│    │ animation│   │ animation│   │ animation│               │
│    │ engine   │   │ engine   │   │ engine   │               │
│    └────┬────┘   └────┬────┘   └────┬────┘               │
│         │             │             │                      │
│    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐               │
│    │ LEDs    │   │ LEDs    │   │ LEDs    │               │
│    │ Zone 1  │   │ Zone 2  │   │ Zone 3  │               │
│    └─────────┘   └─────────┘   └─────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Data Flow:
RPi sends: {animation: "rainbow", speed: 1.5, hue_offset: 0, timestamp: 1234567.890}
ESP32 receives: State, updates local parameters
ESP32 calculates: Frames locally using state + current time
ESP32 renders: At perfect 60 FPS timing

Bandwidth Required:
• State change: ~100 bytes (occasional, not per frame)
• Sync pulse: ~20 bytes every second
• Total: <1 KB/s (vs 180 KB/s for raw frames!)
```

**Pros:**
- Minimal bandwidth (state, not frames)
- Network latency doesn't cause jitter (local rendering)
- ESP32 runs independently if RPi disconnects
- Scales to many ESP32s easily
- Uses ESP32's real-time capabilities

**Cons:**
- Animation code duplicated (Python + C++)
- Synchronization requires careful clock management
- More complex ESP32 firmware
- Harder to debug animations

**When to Use:**
- High LED counts
- Wireless connections
- Wearables (intermittent connectivity)
- Multi-ESP32 synchronized installations
- Production systems

---

### Pattern 3: Hybrid (Recommended for Diuna)

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID ARCHITECTURE                       │
│              (Best of Both Worlds for Diuna)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────┐               │
│  │              RPi 4 (Brain)               │               │
│  │                                          │               │
│  │  • Diuna backend (your existing code!)   │               │
│  │  • Web UI + API                          │               │
│  │  • Animation state machine               │               │
│  │  • Complex calculations (AI, music FFT)  │               │
│  │  • NTP server for sync                   │               │
│  │  • Preset/scene storage                  │               │
│  └─────────────────────┬────────────────────┘               │
│                        │                                    │
│          ┌─────────────┼─────────────┐                     │
│          │             │             │                     │
│          │   State + Sync Messages   │                     │
│          │                           │                     │
│          ▼             ▼             ▼                     │
│    ┌───────────┐ ┌───────────┐ ┌───────────┐             │
│    │  ESP32    │ │  ESP32    │ │  ESP32    │             │
│    │  Wearable │ │  Ambient  │ │  Matrix   │             │
│    │           │ │           │ │           │             │
│    │ • Local   │ │ • Local   │ │ • Local   │             │
│    │   render  │ │   render  │ │   render  │             │
│    │ • Sensors │ │ • Motion  │ │ • Games   │             │
│    │ • Buttons │ │   detect  │ │ • Effects │             │
│    └─────┬─────┘ └─────┬─────┘ └─────┬─────┘             │
│          │             │             │                     │
│    ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐             │
│    │ Wearable  │ │ Room LEDs │ │ 8x8 Matrix│             │
│    │ Hoodie    │ │           │ │           │             │
│    └───────────┘ └───────────┘ └───────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Communication Protocol:
1. State Broadcast (UDP multicast, ~10 Hz):
   {
     "type": "state",
     "timestamp": 1234567890.123,
     "animation": {
       "id": "rainbow",
       "speed": 1.5,
       "direction": 1
     },
     "zones": {
       "floor": {"hue": 180, "sat": 100, "bright": 255},
       "lamp": {"hue": 60, "sat": 80, "bright": 200}
     }
   }

2. Sync Pulse (UDP, ~1 Hz):
   {
     "type": "sync",
     "ntp_time": 1234567890.123,
     "beat_phase": 0.5  // For music sync
   }

3. ESP32 → RPi (WebSocket, event-driven):
   {
     "type": "sensor",
     "device": "wearable_1",
     "data": {
       "button_pressed": true,
       "accelerometer": [0.1, -9.8, 0.2],
       "battery": 85
     }
   }
```

---

## The Synchronization Problem

### Why Synchronization Matters

```
Without sync:                    With sync:
┌──────┐ ┌──────┐ ┌──────┐      ┌──────┐ ┌──────┐ ┌──────┐
│ ESP1 │ │ ESP2 │ │ ESP3 │      │ ESP1 │ │ ESP2 │ │ ESP3 │
└──┬───┘ └──┬───┘ └──┬───┘      └──┬───┘ └──┬───┘ └──┬───┘
   │        │        │             │        │        │
   ▼        ▼        ▼             ▼        ▼        ▼
 Frame 5  Frame 3  Frame 7       Frame 5  Frame 5  Frame 5
 
 Result: Chaotic, unsynchronized  Result: Perfect wave effect
 rainbow looks broken            flowing across all devices
```

### Synchronization Approaches

#### Approach 1: NTP (Network Time Protocol)

**What it is:** Standard internet time sync. Accuracy: 1-50ms over LAN.

```
┌─────────────────────────────────────────────────────────────┐
│                    NTP Synchronization                       │
│                                                             │
│                    ┌─────────────┐                          │
│                    │   NTP Pool  │  (Optional: internet)    │
│                    │ pool.ntp.org│                          │
│                    └──────┬──────┘                          │
│                           │                                 │
│                    ┌──────▼──────┐                          │
│                    │    RPi 4    │  (Can be local NTP       │
│                    │ NTP Server  │   server for LAN)        │
│                    └──────┬──────┘                          │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐          │
│    │  ESP32  │      │  ESP32  │      │  ESP32  │          │
│    │ NTP Sync│      │ NTP Sync│      │ NTP Sync│          │
│    └─────────┘      └─────────┘      └─────────┘          │
│                                                             │
│    All ESP32s share same clock (within ~10ms)              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**ESP32 NTP Implementation:**
```cpp
#include <WiFi.h>
#include <time.h>

void setupNTP() {
    configTime(0, 0, "192.168.1.10");  // RPi as NTP server
    // Or: configTime(0, 0, "pool.ntp.org");
}

// Get synchronized time in milliseconds
uint64_t getSyncedTimeMs() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

// Calculate animation frame based on synced time
void calculateFrame() {
    uint64_t now = getSyncedTimeMs();
    float animTime = (now % animationPeriodMs) / 1000.0f;
    // All ESP32s will calculate same frame at same real-world time
}
```

**Pros:**
- Standard protocol, well-supported
- Works over existing WiFi
- Automatic drift correction
- Good enough for most LED applications (~10ms)

**Cons:**
- 10-50ms accuracy (visible for very fast animations)
- Requires network connectivity
- Initial sync takes seconds
- WiFi latency affects accuracy

---

#### Approach 2: Application-Level Sync (Timestamps in Messages)

**What it is:** Include reference timestamp in every state message. ESP32 calculates offset.

```python
# RPi sender (Python)
import time

def broadcast_state(animation_state):
    message = {
        "type": "state",
        "server_time": time.time(),  # Reference timestamp
        "animation": animation_state
    }
    udp_broadcast(message)
```

```cpp
// ESP32 receiver (C++)
double serverTimeOffset = 0;
double lastServerTime = 0;

void handleStateMessage(JsonDocument& doc) {
    double serverTime = doc["server_time"];
    double localTime = millis() / 1000.0;
    
    // Calculate offset between server and local clock
    // Use exponential moving average to smooth jitter
    double newOffset = serverTime - localTime;
    serverTimeOffset = serverTimeOffset * 0.9 + newOffset * 0.1;
}

// Get animation time synchronized with server
double getSyncedAnimationTime() {
    return (millis() / 1000.0) + serverTimeOffset;
}
```

**Pros:**
- No additional protocol needed
- Works immediately (no NTP wait)
- Simple implementation
- Adapts to network delays

**Cons:**
- One-way sync (doesn't account for network latency)
- Accumulates drift over time
- Needs frequent messages to stay synced

---

#### Approach 3: PTP (Precision Time Protocol) - IEEE 1588

**What it is:** Sub-microsecond synchronization. Used in professional AV, broadcast.

```
┌─────────────────────────────────────────────────────────────┐
│                    PTP Synchronization                       │
│                    (Professional Grade)                      │
│                                                             │
│  PTP measures round-trip time to calculate exact offset:    │
│                                                             │
│  RPi (Master) ──── Sync Message ────▶ ESP32 (Slave)        │
│       │                                    │                │
│       ◀──── Delay Request ─────────────────┤                │
│       │                                    │                │
│       ──── Delay Response ─────────────────▶                │
│                                                             │
│  Accuracy: 1-100 microseconds (100x better than NTP!)      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**ESP32 PTP Library:** `esp_ptp` (experimental) or implement simplified version.

**Simplified PTP for LED Sync:**
```cpp
// ESP32 implementation (simplified)
class SimplePTP {
private:
    double offset = 0;
    double delay = 0;
    
public:
    void handleSyncMessage(double serverTime, double t1_send) {
        double t2_receive = micros() / 1000000.0;
        // t1 = server send time
        // t2 = local receive time
        // offset = (t1 - t2) approximately
        // Will be refined with delay measurement
    }
    
    void sendDelayRequest() {
        double t3_send = micros() / 1000000.0;
        // Send request to server
    }
    
    void handleDelayResponse(double t4_receive_at_server) {
        // Now we have:
        // t1 = sync send time (server)
        // t2 = sync receive time (local)
        // t3 = delay request send time (local)
        // t4 = delay request receive time (server)
        
        // offset = ((t2 - t1) + (t4 - t3)) / 2
        // delay = ((t2 - t1) - (t4 - t3)) / 2
    }
    
    double getSyncedTime() {
        return (micros() / 1000000.0) + offset;
    }
};
```

**Pros:**
- Microsecond accuracy
- Accounts for network asymmetry
- Industry standard

**Cons:**
- Complex implementation
- Overkill for LEDs (you won't see 100µs difference)
- Limited ESP32 support

---

#### Approach 4: Beat Sync (Music/BPM)

**What it is:** Sync to musical beats, not wall-clock time.

```
┌─────────────────────────────────────────────────────────────┐
│                      Beat Synchronization                    │
│                      (For Music Reactive)                    │
│                                                             │
│  ┌─────────────┐                                            │
│  │   RPi 4     │                                            │
│  │             │  Audio Analysis:                           │
│  │ ┌─────────┐ │  • Detect BPM                             │
│  │ │ Audio   │ │  • Track beat phase                        │
│  │ │ Input   │ │  • Broadcast beat events                   │
│  │ └─────────┘ │                                            │
│  └──────┬──────┘                                            │
│         │                                                   │
│         │  {                                                │
│         │    "type": "beat",                                │
│         │    "bpm": 120,                                    │
│         │    "phase": 0.0,  // 0.0-1.0 within beat         │
│         │    "beat_num": 42,                                │
│         │    "timestamp": 1234567890.123                    │
│         │  }                                                │
│         │                                                   │
│         ▼                                                   │
│    ┌─────────┐                                              │
│    │  ESP32  │  Local beat tracking:                       │
│    │         │  • Receive beat messages                    │
│    │         │  • Interpolate between beats                │
│    │         │  • Sync animations to beat phase            │
│    └─────────┘                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
```cpp
// ESP32 beat tracker
class BeatTracker {
private:
    float bpm = 120;
    float lastBeatPhase = 0;
    uint64_t lastBeatTime = 0;
    float msPerBeat;
    
public:
    void updateFromServer(float newBpm, float phase, uint64_t serverTime) {
        bpm = newBpm;
        msPerBeat = 60000.0 / bpm;
        lastBeatPhase = phase;
        lastBeatTime = serverTime;
    }
    
    // Get current beat phase (0.0 - 1.0)
    float getBeatPhase() {
        uint64_t now = getSyncedTimeMs();
        float elapsed = (now - lastBeatTime);
        float beatProgress = elapsed / msPerBeat;
        return fmod(lastBeatPhase + beatProgress, 1.0);
    }
    
    // Check if we're on a beat (within tolerance)
    bool isOnBeat(float tolerance = 0.1) {
        float phase = getBeatPhase();
        return phase < tolerance || phase > (1.0 - tolerance);
    }
};
```

---

### Recommended Sync Strategy for Diuna

```
┌─────────────────────────────────────────────────────────────┐
│              RECOMMENDED SYNC STRATEGY                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Use NTP for coarse sync (all ESP32s within ~20ms)       │
│     - RPi runs local NTP server (chrony or ntpd)           │
│     - ESP32s sync on boot                                   │
│                                                             │
│  2. Use application-level timestamps for fine sync          │
│     - Every state message includes server timestamp         │
│     - ESP32 tracks offset with EMA filter                   │
│                                                             │
│  3. Animations use deterministic time-based functions       │
│     - rainbow(t) = hue at time t                           │
│     - All ESP32s calculate same result for same t          │
│                                                             │
│  4. For music, use beat-relative phase                      │
│     - Don't sync to wall clock for music                   │
│     - Sync to beat phase (more resilient to network jitter)│
│                                                             │
│  Result: Visible sync accuracy ~5-10ms (imperceptible)      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Frame Streaming vs State Streaming

### The Core Decision

This is your key question. Let me break it down clearly:

### Option A: Stream Frames (Pixels)

```
RPi calculates: frame[0] = [(255,0,0), (254,0,1), (253,0,2), ...]
                frame[1] = [(254,0,1), (253,0,2), (252,0,3), ...]
                frame[2] = [(253,0,2), (252,0,3), (251,0,4), ...]
                ...

Sends to ESP32: Raw bytes at 60 FPS

ESP32 code:
void loop() {
    if (receiveFrame(buffer)) {
        writeToStrip(buffer);
    }
}
```

**Data Requirements:**
| LEDs | Bytes/Frame | @ 60 FPS | @ 30 FPS |
|------|-------------|----------|----------|
| 50   | 150 B       | 9 KB/s   | 4.5 KB/s |
| 100  | 300 B       | 18 KB/s  | 9 KB/s   |
| 300  | 900 B       | 54 KB/s  | 27 KB/s  |
| 500  | 1500 B      | 90 KB/s  | 45 KB/s  |
| 1000 | 3000 B      | 180 KB/s | 90 KB/s  |

**Problems:**
1. **Latency = Jitter:** Network delay varies (5-50ms WiFi). Frame arrives late = visual stutter.
2. **Packet Loss = Glitch:** Lost UDP packet = missing frame = visible glitch.
3. **Bandwidth:** 1000 LEDs = 180 KB/s. Multiply by 5 ESP32s = 900 KB/s constant.
4. **No Resilience:** RPi offline = ESP32 goes dark.

### Option B: Stream State (Parameters)

```
RPi calculates: state = {
    animation: "rainbow",
    speed: 1.5,
    offset: 0.3,
    brightness: 200,
    timestamp: 1234567890.123
}

Sends to ESP32: State message (once per change, or ~10 Hz heartbeat)

ESP32 code:
void loop() {
    float t = getSyncedTime();
    float animPhase = fmod(t * state.speed + state.offset, 1.0);
    
    for (int i = 0; i < NUM_LEDS; i++) {
        float pixelPhase = fmod(animPhase + i * 0.02, 1.0);
        leds[i] = CHSV(pixelPhase * 255, 255, state.brightness);
    }
    
    FastLED.show();
    delay(16);  // 60 FPS
}
```

**Data Requirements:**
| Event | Size | Frequency | Bandwidth |
|-------|------|-----------|-----------|
| State change | ~200 B | Per change | Variable |
| Heartbeat | ~50 B | 1 Hz | 50 B/s |
| Sync pulse | ~20 B | 1 Hz | 20 B/s |
| **Total** | - | - | **<1 KB/s** |

**Benefits:**
1. **Latency Tolerant:** Late packet just means slightly delayed state change.
2. **Packet Loss Tolerant:** Next heartbeat will resync. No visible glitch.
3. **Low Bandwidth:** <1 KB/s vs 180 KB/s. Massive difference.
4. **Resilient:** ESP32 continues animation if RPi offline.
5. **Scalable:** Same bandwidth for 1 or 100 ESP32s (multicast).

### Verdict: Stream State, Not Frames

```
┌─────────────────────────────────────────────────────────────┐
│                      RECOMMENDATION                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ Stream ANIMATION STATE                                  │
│     - Animation ID, parameters, timestamp                   │
│     - Low bandwidth, resilient, scalable                    │
│                                                             │
│  ❌ Don't stream RAW FRAMES                                 │
│     - High bandwidth, latency-sensitive, fragile            │
│                                                             │
│  Exception: Complex/AI-generated animations that can't      │
│  be expressed as deterministic functions may need frames.   │
│  In that case, consider keyframe interpolation.             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### Deterministic Time-Based Animations

**What does "deterministic time-based" mean?**

```
Given the same INPUT (time + parameters), always produce the same OUTPUT (pixel colors).

rainbow(t=1.5, speed=2.0, offset=0.0) → ALWAYS returns hue 180°
rainbow(t=1.5, speed=2.0, offset=0.0) → ALWAYS returns hue 180°

No randomness. No accumulated state. Pure function of time.
```

**Example - Rainbow Animation (Deterministic):**

```cpp
// ESP32 code
CRGB calculateRainbow(float t, int pixelIndex, AnimationParams& params) {
    // t = synchronized time in seconds
    // Pure function: same inputs → same output
    
    float speed = params.speed;            // e.g., 1.5
    float wavelength = params.wavelength;  // e.g., 0.5 (50% of strip)
    
    // Phase progresses over time
    float phase = fmod(t * speed, 1.0);
    
    // Each pixel is offset in phase
    float pixelOffset = (float)pixelIndex / NUM_LEDS;
    float pixelPhase = fmod(phase + pixelOffset / wavelength, 1.0);
    
    // Convert phase to hue
    uint8_t hue = pixelPhase * 255;
    
    return CHSV(hue, 255, 255);
}

void loop() {
    float t = getSyncedTime();  // NTP-synced time
    
    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = calculateRainbow(t, i, currentParams);
    }
    
    FastLED.show();
}
```

**Why This Works:**
- All ESP32s have same synced time `t`
- All ESP32s have same parameters (from RPi broadcast)
- Pure function: `rainbow(t, params)` → same everywhere
- Result: Perfectly synchronized across all devices!

**Animations That ARE Deterministic:**
- Rainbow/color cycle (hue = f(time))
- Sine wave/breathing (brightness = sin(time))
- Chase/marquee (position = time mod length)
- Gradient sweep (blend between colors over time)
- Wave patterns (sin(position + time))

**Animations That Are NOT Easily Deterministic:**
- Particle systems (random spawning)
- Fire effects (random flicker)
- Music reactive (external input)
- AI-generated patterns (neural network output)
- Physics simulations (accumulated state)

**Solution for Non-Deterministic Animations:**

```cpp
// Use seeded random with time-based seed
void fireEffect(float t) {
    // Reset random seed based on frame number
    uint32_t frameNum = (uint32_t)(t * 60);  // 60 FPS
    randomSeed(frameNum);  // Same seed → same "random" sequence
    
    // Now random() will produce same values on all ESP32s!
    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i].r = random(200, 255);
        leds[i].g = random(50, 150);
        leds[i].b = 0;
    }
}
```

---

## Practical Recommendations for Diuna

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                DIUNA + ESP32 ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    RPi 4 (Diuna Core)                │   │
│  │                                                      │   │
│  │  Your existing code:                                 │   │
│  │  • FastAPI backend                                   │   │
│  │  • ZoneService, AnimationService                     │   │
│  │  • FrameManager (for local RPi LEDs)                 │   │
│  │  • Web UI (React)                                    │   │
│  │                                                      │   │
│  │  NEW: ESP32 Bridge Service                           │   │
│  │  • UDP multicast broadcaster                         │   │
│  │  • State serialization                               │   │
│  │  • NTP server (chrony)                               │   │
│  │  • ESP32 registry (discovered devices)               │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           │ UDP Multicast                   │
│                           │ 239.1.2.3:5000                  │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│         ▼                 ▼                 ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   ESP32     │  │   ESP32     │  │   ESP32     │        │
│  │  Wearable   │  │   Ambient   │  │   Matrix    │        │
│  │             │  │             │  │             │        │
│  │ • FastLED   │  │ • FastLED   │  │ • FastLED   │        │
│  │ • Anim Lib  │  │ • Anim Lib  │  │ • Anim Lib  │        │
│  │ • Sensors   │  │ • PIR       │  │ • Gamepad   │        │
│  │ • BLE       │  │             │  │             │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │
│    ┌────▼────┐     ┌────▼────┐     ┌────▼────┐            │
│    │ Hoodie  │     │ Room    │     │ 16x16   │            │
│    │ 150 LEDs│     │ 300 LEDs│     │ Matrix  │            │
│    └─────────┘     └─────────┘     └─────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Protocol Design

```python
# src/esp32/protocol.py

from dataclasses import dataclass
from enum import Enum
import json
import struct
import socket
import time

class MessageType(Enum):
    STATE = 0x01      # Full animation state
    SYNC = 0x02       # Time sync pulse
    COMMAND = 0x03    # Direct command (instant)
    CONFIG = 0x04     # Configuration update
    HEARTBEAT = 0x05  # Keep-alive

@dataclass
class AnimationState:
    animation_id: str
    speed: float
    params: dict
    
@dataclass
class StateMessage:
    type: MessageType = MessageType.STATE
    timestamp: float = 0.0
    animations: dict = None  # zone_id -> AnimationState
    zones: dict = None       # zone_id -> {hue, sat, bright}
    
    def to_bytes(self) -> bytes:
        """Serialize to compact binary format"""
        # Header: [type: 1B][timestamp: 8B][payload_len: 2B]
        payload = json.dumps({
            "animations": self.animations,
            "zones": self.zones
        }).encode()
        
        header = struct.pack(
            ">BdH",
            self.type.value,
            self.timestamp,
            len(payload)
        )
        
        return header + payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'StateMessage':
        """Deserialize from binary"""
        type_val, timestamp, payload_len = struct.unpack(">BdH", data[:11])
        payload = json.loads(data[11:11+payload_len])
        
        return cls(
            type=MessageType(type_val),
            timestamp=timestamp,
            animations=payload.get("animations"),
            zones=payload.get("zones")
        )

class ESP32Broadcaster:
    """Broadcasts state to all ESP32 devices via UDP multicast"""
    
    MULTICAST_GROUP = "239.1.2.3"
    PORT = 5000
    
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        
    def broadcast_state(self, state: StateMessage):
        """Send state to all ESP32s"""
        state.timestamp = time.time()
        data = state.to_bytes()
        self.sock.sendto(data, (self.MULTICAST_GROUP, self.PORT))
        
    def broadcast_sync(self):
        """Send sync pulse"""
        msg = struct.pack(">Bd", MessageType.SYNC.value, time.time())
        self.sock.sendto(msg, (self.MULTICAST_GROUP, self.PORT))
```

### ESP32 Firmware Structure

```
esp32_firmware/
├── platformio.ini
├── src/
│   ├── main.cpp
│   ├── config.h
│   ├── communication/
│   │   ├── wifi_manager.cpp
│   │   ├── udp_receiver.cpp
│   │   └── protocol_parser.cpp
│   ├── animation/
│   │   ├── animation_engine.cpp
│   │   ├── rainbow.cpp
│   │   ├── breathe.cpp
│   │   ├── fire.cpp
│   │   └── wave.cpp
│   ├── sync/
│   │   ├── time_sync.cpp
│   │   └── ntp_client.cpp
│   └── hardware/
│       ├── led_strip.cpp
│       └── sensors.cpp
└── lib/
    └── (FastLED, ArduinoJson, etc.)
```

**Main.cpp Skeleton:**
```cpp
#include <FastLED.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include "config.h"
#include "animation_engine.h"
#include "time_sync.h"

// LED Configuration
#define NUM_LEDS 150
#define LED_PIN 5
CRGB leds[NUM_LEDS];

// Network
WiFiUDP udp;
TimeSync timeSync;
AnimationEngine animEngine;

// State
AnimationState currentState;
bool stateUpdated = false;

void setup() {
    Serial.begin(115200);
    
    // Initialize LEDs
    FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, NUM_LEDS);
    FastLED.setBrightness(255);
    
    // Connect WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) delay(100);
    
    // Setup NTP
    timeSync.begin(NTP_SERVER);
    
    // Join multicast group
    udp.beginMulticast(IPAddress(239, 1, 2, 3), 5000);
    
    // Initialize animation engine
    animEngine.begin(leds, NUM_LEDS);
}

void loop() {
    // Check for incoming messages
    int packetSize = udp.parsePacket();
    if (packetSize > 0) {
        handlePacket();
    }
    
    // Update animation
    float t = timeSync.getSyncedTime();
    animEngine.update(t, currentState);
    
    // Render LEDs
    FastLED.show();
    
    // Target 60 FPS
    delay(16);
}

void handlePacket() {
    uint8_t buffer[512];
    int len = udp.read(buffer, sizeof(buffer));
    
    // Parse message type
    uint8_t msgType = buffer[0];
    
    switch (msgType) {
        case 0x01: // STATE
            parseStateMessage(buffer, len);
            break;
        case 0x02: // SYNC
            double serverTime;
            memcpy(&serverTime, buffer + 1, 8);
            timeSync.updateOffset(serverTime);
            break;
    }
}

void parseStateMessage(uint8_t* data, int len) {
    // Parse header
    double timestamp;
    uint16_t payloadLen;
    memcpy(&timestamp, data + 1, 8);
    memcpy(&payloadLen, data + 9, 2);
    
    // Parse JSON payload
    StaticJsonDocument<512> doc;
    deserializeJson(doc, (char*)(data + 11), payloadLen);
    
    // Update current state
    if (doc.containsKey("animations")) {
        // Update animation parameters
        JsonObject anims = doc["animations"];
        // ... parse and apply
    }
    
    stateUpdated = true;
}
```

---

## ESP32 Project Ideas

### For Your LED/Wearable Project

#### 1. Wearable Controller Module

```
┌─────────────────────────────────────────────────────────────┐
│              ESP32 WEARABLE MODULE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Features:                                                  │
│  • Controls hoodie LEDs independently                       │
│  • Accelerometer for motion-reactive effects               │
│  • Capacitive touch buttons (no physical buttons)          │
│  • LiPo battery + charging circuit                         │
│  • BLE for phone app control                               │
│  • WiFi for sync with Diuna                                │
│  • Offline mode (stored presets when no WiFi)              │
│                                                             │
│  Hardware:                                                  │
│  • ESP32-S3 (BLE 5.0, more GPIOs)                          │
│  • MPU6050/LSM6DS3 (accelerometer + gyro)                  │
│  • TP4056 (LiPo charger)                                   │
│  • 3.7V 2000mAh LiPo                                       │
│  • WS2812B strips (150 LEDs)                               │
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │  Motion-Reactive Animations:                     │       │
│  │  • Walk detection → gentle pulse                │       │
│  │  • Jump → explosion effect                      │       │
│  │  • Spin → rainbow spiral                        │       │
│  │  • Shake → random sparkle                       │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Distributed Ambient Lighting

```
┌─────────────────────────────────────────────────────────────┐
│           MULTI-ROOM SYNCHRONIZED LIGHTING                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Living Room                    Bedroom                     │
│  ┌─────────────┐               ┌─────────────┐             │
│  │   ESP32     │               │   ESP32     │             │
│  │  • Ceiling  │    Sync       │  • Bed frame│             │
│  │  • TV back  │◀═══════════▶│  • Closet   │             │
│  │  • Floor    │               │  • Reading  │             │
│  └─────────────┘               └─────────────┘             │
│                                                             │
│  Kitchen                        Office                      │
│  ┌─────────────┐               ┌─────────────┐             │
│  │   ESP32     │               │   ESP32     │             │
│  │  • Counter  │◀═══════════▶│  • Desk     │             │
│  │  • Cabinet  │               │  • Monitor  │             │
│  └─────────────┘               └─────────────┘             │
│                                                             │
│  All rooms sync: color, animation, brightness               │
│  Individual control: per-room scenes, sensors               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Interactive LED Matrix

```
┌─────────────────────────────────────────────────────────────┐
│               16x16 LED MATRIX MODULE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────┐                │
│  │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○        │                │
│  │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○        │                │
│  │ ○ ○ ● ● ● ○ ○ ○ ○ ○ ● ● ● ○ ○ ○        │  Snake Game!  │
│  │ ○ ○ ● ○ ○ ○ ○ ○ ○ ○ ○ ○ ● ○ ○ ○        │                │
│  │ ○ ○ ● ○ ○ ○ ○ ○ ○ ○ ○ ○ ● ○ ○ ○        │  Also:        │
│  │ ○ ○ ● ● ● ● ● ● ● ● ● ● ● ○ ○ ○        │  • Pong       │
│  │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○        │  • Tetris     │
│  │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○        │  • Visualizer │
│  │ ○ ○ ○ ○ ○ ○ ○ ● ○ ○ ○ ○ ○ ○ ○ ○        │  • Clock      │
│  │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○        │  • Alerts     │
│  └────────────────────────────────────────┘                │
│                                                             │
│  ESP32 Features:                                            │
│  • 256 WS2812B in 16x16 grid                               │
│  • Local game logic                                         │
│  • Rotary encoder for input                                │
│  • Web control via Diuna                                    │
│  • MQTT notifications                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4. Sensor Integration Node

```
┌─────────────────────────────────────────────────────────────┐
│              ESP32 SENSOR + LED NODE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Inputs:                       Outputs:                     │
│  ┌─────────────────┐          ┌─────────────────┐          │
│  │ • PIR motion    │          │ • LED strip     │          │
│  │ • Light sensor  │   ESP32  │ • Status LED    │          │
│  │ • Temperature   │◀────────▶│ • Relay (optional)│        │
│  │ • Sound/mic     │          │                 │          │
│  │ • Door contact  │          │                 │          │
│  └─────────────────┘          └─────────────────┘          │
│                                                             │
│  Logic (runs locally):                                      │
│  • Motion detected → fade in lights                        │
│  • No motion 5min → fade out lights                        │
│  • Dark + motion → full brightness                         │
│  • Light + motion → dim brightness                         │
│  • Sound level → reactive colors                           │
│                                                             │
│  Reports to RPi:                                            │
│  • Sensor readings                                          │
│  • Occupancy status                                         │
│  • Energy usage estimation                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### For Your Bigger Vision (Printhouse/Smart Everything)

#### 5. Production Line Status Display

```
┌─────────────────────────────────────────────────────────────┐
│           PRODUCTION LINE LED STATUS SYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Mimaki Printer     Cutting Plotter    Laminator           │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│  │  ESP32 +    │   │  ESP32 +    │   │  ESP32 +    │      │
│  │  LED Ring   │   │  LED Ring   │   │  LED Ring   │      │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘      │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│                    ┌──────▼──────┐                         │
│                    │   RPi 4     │                         │
│                    │ (Dashboard) │                         │
│                    └─────────────┘                         │
│                                                             │
│  LED Ring Status:                                           │
│  🟢 Green pulse     → Ready/Idle                           │
│  🔵 Blue animation  → Printing/Cutting                     │
│  🟡 Yellow flash    → Attention needed (ink/material)      │
│  🔴 Red solid       → Error/Stopped                        │
│  🌈 Rainbow         → Job complete!                        │
│                                                             │
│  Integration:                                               │
│  • Serial from Mimaki for status                           │
│  • GPIO from plotter sensors                               │
│  • MQTT to central dashboard                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 6. Interactive Storefront Display

```
┌─────────────────────────────────────────────────────────────┐
│            INTERACTIVE STOREFRONT/EXHIBITION                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 WINDOW DISPLAY                       │   │
│  │                                                      │   │
│  │   ┌───────────────────────────────────────┐         │   │
│  │   │     LED MATRIX / STRIP DISPLAY        │         │   │
│  │   │                                       │         │   │
│  │   │     ESP32 controlled                  │         │   │
│  │   │                                       │         │   │
│  │   └───────────────────────────────────────┘         │   │
│  │                     │                               │   │
│  │   ┌────────────────┼────────────────┐              │   │
│  │   │                │                │              │   │
│  │   ▼                ▼                ▼              │   │
│  │ [PIR]          [ToF Sensor]     [Camera]          │   │
│  │ Motion         Distance         Gesture           │   │
│  │ Detection      Tracking         Recognition       │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Interactive Behaviors:                                     │
│  • Person approaches → display wakes up                    │
│  • Person stays → product showcase animation               │
│  • Hand gesture → change display/product                   │
│  • Multiple people → synchronized show                     │
│  • Night mode → ambient/artistic animation                 │
│                                                             │
│  Integration with Diuna:                                    │
│  • Schedule different displays                              │
│  • A/B test animations                                      │
│  • Track engagement metrics                                 │
│  • Remote content updates                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 7. Smart Workspace Environment

```
┌─────────────────────────────────────────────────────────────┐
│             SMART WORKSPACE ENVIRONMENT                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Circadian Lighting:                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 6AM        12PM        6PM        10PM     12AM    │   │
│  │  │          │          │          │         │       │   │
│  │  ▼          ▼          ▼          ▼         ▼       │   │
│  │ Cool      Neutral     Warm      Dim warm   Off      │   │
│  │ 6500K     4000K      3000K      2700K              │   │
│  │ Energize  Productive  Wind down  Relax             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Per-Workstation ESP32:                                     │
│  • Personal color preference                               │
│  • Presence detection (auto on/off)                        │
│  • Focus mode (red "do not disturb" light)                │
│  • Meeting mode (collaborative lighting)                   │
│  • Break reminder (gentle pulse)                           │
│                                                             │
│  Integration:                                               │
│  • Calendar sync (meeting lights)                          │
│  • Pomodoro timer integration                              │
│  • Slack status → desk light                               │
│  • Music visualization during breaks                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 8. LED Art Installation Controller

```
┌─────────────────────────────────────────────────────────────┐
│              LARGE-SCALE ART INSTALLATION                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Architecture:                                              │
│                                                             │
│                    ┌─────────────┐                         │
│                    │   RPi 4     │                         │
│                    │  (Master)   │                         │
│                    └──────┬──────┘                         │
│                           │                                │
│      ┌────────────────────┼────────────────────┐          │
│      │                    │                    │          │
│   ┌──▼───┐            ┌───▼───┐           ┌───▼───┐      │
│   │ESP32 │            │ESP32  │           │ESP32  │      │
│   │Sect 1│            │Sect 2 │           │Sect 3 │      │
│   │      │            │       │           │       │      │
│   │500LED│            │500LED │           │500LED │      │
│   └──────┘            └───────┘           └───────┘      │
│                                                             │
│  Synchronized animations across 1500+ LEDs                  │
│  Each ESP32: independent section, synced via NTP            │
│                                                             │
│  Features:                                                  │
│  • Generative art algorithms                               │
│  • Music reactive (BPM sync)                               │
│  • Time-of-day themes                                       │
│  • Remote control for events                               │
│  • Recording/playback modes                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Examples

### Complete ESP32 Receiver Code

```cpp
// ESP32 Diuna Client - Complete Implementation
// platformio.ini: platform = espressif32, framework = arduino
// lib_deps = fastled/FastLED, bblanchon/ArduinoJson

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <FastLED.h>
#include <ArduinoJson.h>
#include <time.h>

// ============== CONFIGURATION ==============
const char* WIFI_SSID = "YourNetwork";
const char* WIFI_PASS = "YourPassword";
const char* NTP_SERVER = "192.168.1.10";  // RPi IP

#define NUM_LEDS 150
#define LED_PIN 5
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

const IPAddress MULTICAST_IP(239, 1, 2, 3);
const uint16_t MULTICAST_PORT = 5000;

// ============== GLOBALS ==============
CRGB leds[NUM_LEDS];
WiFiUDP udp;

// Time synchronization
double timeOffset = 0;
uint64_t lastSyncTime = 0;

// Animation state
struct AnimState {
    uint8_t animationId = 0;  // 0=static, 1=rainbow, 2=breathe, 3=wave, 4=fire
    float speed = 1.0;
    float param1 = 0.0;
    float param2 = 0.0;
    uint8_t hue = 0;
    uint8_t saturation = 255;
    uint8_t brightness = 255;
} state;

// ============== TIME SYNC ==============
void setupNTP() {
    configTime(0, 0, NTP_SERVER);
    
    Serial.print("Waiting for NTP sync");
    time_t now = time(nullptr);
    while (now < 8 * 3600 * 2) {
        delay(100);
        Serial.print(".");
        now = time(nullptr);
    }
    Serial.println(" synced!");
}

double getSyncedTime() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec / 1000000.0 + timeOffset;
}

void updateTimeOffset(double serverTime) {
    double localTime = millis() / 1000.0;
    double newOffset = serverTime - localTime;
    
    // Exponential moving average for smooth adjustment
    timeOffset = timeOffset * 0.9 + newOffset * 0.1;
    lastSyncTime = millis();
}

// ============== ANIMATIONS ==============
// All animations are deterministic functions of time

void animStatic() {
    fill_solid(leds, NUM_LEDS, CHSV(state.hue, state.saturation, state.brightness));
}

void animRainbow(double t) {
    float phase = fmod(t * state.speed, 1.0);
    
    for (int i = 0; i < NUM_LEDS; i++) {
        float pixelPhase = fmod(phase + (float)i / NUM_LEDS, 1.0);
        leds[i] = CHSV(pixelPhase * 255, state.saturation, state.brightness);
    }
}

void animBreathe(double t) {
    float phase = fmod(t * state.speed, 1.0);
    float breath = (sin(phase * 2 * PI) + 1.0) / 2.0;  // 0-1
    uint8_t val = breath * state.brightness;
    
    fill_solid(leds, NUM_LEDS, CHSV(state.hue, state.saturation, val));
}

void animWave(double t) {
    float phase = fmod(t * state.speed, 1.0);
    float wavelength = state.param1 > 0 ? state.param1 : 0.25;  // Default 25% of strip
    
    for (int i = 0; i < NUM_LEDS; i++) {
        float pos = (float)i / NUM_LEDS;
        float wave = sin((pos / wavelength + phase) * 2 * PI);
        float brightness = (wave + 1.0) / 2.0;  // 0-1
        
        leds[i] = CHSV(state.hue, state.saturation, brightness * state.brightness);
    }
}

void animFire(double t) {
    // Deterministic fire using time-based seed
    uint32_t frameSeed = (uint32_t)(t * 30);  // 30 FPS fire
    
    for (int i = 0; i < NUM_LEDS; i++) {
        // Generate consistent "random" values
        uint32_t seed = frameSeed * NUM_LEDS + i;
        uint8_t heat = ((seed * 1103515245 + 12345) >> 16) % 256;
        
        // Heat rises (LEDs at end are cooler)
        float cooling = (float)i / NUM_LEDS * 0.5;
        heat = max(0, heat - (int)(cooling * 100));
        
        // Map heat to color
        leds[i] = HeatColor(heat);
    }
}

void updateAnimation(double t) {
    switch (state.animationId) {
        case 0: animStatic(); break;
        case 1: animRainbow(t); break;
        case 2: animBreathe(t); break;
        case 3: animWave(t); break;
        case 4: animFire(t); break;
        default: animStatic(); break;
    }
}

// ============== PROTOCOL HANDLING ==============
void handleStateMessage(uint8_t* data, int len) {
    // Skip header: type(1) + timestamp(8) + payloadLen(2) = 11 bytes
    double timestamp;
    uint16_t payloadLen;
    memcpy(&timestamp, data + 1, 8);
    memcpy(&payloadLen, data + 9, 2);
    
    // Update time offset
    updateTimeOffset(timestamp);
    
    // Parse JSON payload
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, (char*)(data + 11), payloadLen);
    
    if (err) {
        Serial.print("JSON parse error: ");
        Serial.println(err.c_str());
        return;
    }
    
    // Update animation state
    if (doc.containsKey("animation")) {
        JsonObject anim = doc["animation"];
        state.animationId = anim["id"] | 0;
        state.speed = anim["speed"] | 1.0;
        state.param1 = anim["param1"] | 0.0;
        state.param2 = anim["param2"] | 0.0;
    }
    
    // Update zone state (for this ESP32's zone)
    if (doc.containsKey("zone")) {
        JsonObject zone = doc["zone"];
        state.hue = zone["hue"] | 0;
        state.saturation = zone["sat"] | 255;
        state.brightness = zone["bright"] | 255;
    }
    
    Serial.printf("State updated: anim=%d, speed=%.2f, hue=%d\n", 
                  state.animationId, state.speed, state.hue);
}

void handleSyncMessage(uint8_t* data, int len) {
    double serverTime;
    memcpy(&serverTime, data + 1, 8);
    updateTimeOffset(serverTime);
}

void checkIncoming() {
    int packetSize = udp.parsePacket();
    if (packetSize > 0) {
        uint8_t buffer[512];
        int len = udp.read(buffer, sizeof(buffer));
        
        if (len > 0) {
            uint8_t msgType = buffer[0];
            
            switch (msgType) {
                case 0x01: // STATE
                    handleStateMessage(buffer, len);
                    break;
                case 0x02: // SYNC
                    handleSyncMessage(buffer, len);
                    break;
            }
        }
    }
}

// ============== SETUP & LOOP ==============
void setup() {
    Serial.begin(115200);
    Serial.println("\n\nDiuna ESP32 Client Starting...");
    
    // Initialize LEDs
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(255);
    fill_solid(leds, NUM_LEDS, CRGB::Black);
    FastLED.show();
    
    // Connect WiFi
    Serial.printf("Connecting to %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(100);
        Serial.print(".");
        
        // Show connecting animation
        static uint8_t hue = 0;
        fill_solid(leds, 5, CHSV(hue++, 255, 100));
        FastLED.show();
    }
    Serial.println(" connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    
    // Setup NTP
    setupNTP();
    
    // Join multicast group
    if (udp.beginMulticast(MULTICAST_IP, MULTICAST_PORT)) {
        Serial.println("Joined multicast group");
    } else {
        Serial.println("Failed to join multicast!");
    }
    
    // Startup animation
    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CRGB::Green;
        FastLED.show();
        delay(10);
    }
    delay(500);
    fill_solid(leds, NUM_LEDS, CRGB::Black);
    FastLED.show();
    
    Serial.println("Ready!");
}

void loop() {
    // Process incoming messages
    checkIncoming();
    
    // Get synchronized time
    double t = getSyncedTime();
    
    // Update animation based on current state and time
    updateAnimation(t);
    
    // Show LEDs
    FastLED.show();
    
    // Target ~60 FPS
    delay(16);
}
```

### RPi Broadcaster Service

```python
# src/esp32/broadcaster.py
"""
ESP32 State Broadcaster Service
Integrates with existing Diuna architecture
"""

import asyncio
import json
import socket
import struct
import time
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any
from enum import Enum

from services.event_bus import EventBus
from services.zone_service import ZoneService
from services.animation_service import AnimationService
from models.enums import ZoneID, AnimationID
from utils.logger2 import BoundLogger

log = BoundLogger.for_category("esp32_broadcaster")


class MessageType(Enum):
    STATE = 0x01
    SYNC = 0x02
    COMMAND = 0x03
    CONFIG = 0x04


@dataclass
class ESP32ZoneMapping:
    """Maps Diuna zones to ESP32 devices"""
    zone_id: ZoneID
    esp32_id: str
    led_count: int
    led_offset: int = 0  # For zones that span multiple strips


class ESP32Broadcaster:
    """
    Broadcasts animation state to ESP32 devices via UDP multicast.
    
    This is the bridge between Diuna's Python backend and ESP32 firmware.
    """
    
    MULTICAST_GROUP = "239.1.2.3"
    MULTICAST_PORT = 5000
    STATE_BROADCAST_HZ = 10  # State updates per second
    SYNC_BROADCAST_HZ = 1    # Sync pulses per second
    
    def __init__(
        self,
        zone_service: ZoneService,
        animation_service: AnimationService,
        event_bus: EventBus,
        zone_mappings: Optional[Dict[ZoneID, ESP32ZoneMapping]] = None
    ):
        self.zone_service = zone_service
        self.animation_service = animation_service
        self.event_bus = event_bus
        self.zone_mappings = zone_mappings or {}
        
        # UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        
        # State tracking
        self._running = False
        self._last_state: Dict[str, Any] = {}
        
        # Tasks
        self._state_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None
        
        log.info("ESP32 Broadcaster initialized")
    
    async def start(self):
        """Start broadcasting tasks"""
        self._running = True
        
        # Subscribe to relevant events
        self.event_bus.subscribe("zone_state_changed", self._on_zone_changed)
        self.event_bus.subscribe("animation_started", self._on_animation_started)
        self.event_bus.subscribe("animation_stopped", self._on_animation_stopped)
        
        # Start background tasks
        self._state_task = asyncio.create_task(self._state_broadcast_loop())
        self._sync_task = asyncio.create_task(self._sync_broadcast_loop())
        
        log.info("ESP32 Broadcaster started", 
                 state_hz=self.STATE_BROADCAST_HZ,
                 sync_hz=self.SYNC_BROADCAST_HZ)
    
    async def stop(self):
        """Stop broadcasting"""
        self._running = False
        
        if self._state_task:
            self._state_task.cancel()
            try:
                await self._state_task
            except asyncio.CancelledError:
                pass
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        log.info("ESP32 Broadcaster stopped")
    
    # ==================== Broadcasting ====================
    
    async def _state_broadcast_loop(self):
        """Periodically broadcast current state"""
        interval = 1.0 / self.STATE_BROADCAST_HZ
        
        while self._running:
            try:
                await self._broadcast_full_state()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("State broadcast error", error=str(e))
                await asyncio.sleep(1)  # Back off on error
    
    async def _sync_broadcast_loop(self):
        """Periodically broadcast sync pulses"""
        interval = 1.0 / self.SYNC_BROADCAST_HZ
        
        while self._running:
            try:
                self._send_sync_pulse()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("Sync broadcast error", error=str(e))
                await asyncio.sleep(1)
    
    async def _broadcast_full_state(self):
        """Gather and broadcast complete system state"""
        state = self._build_state_message()
        
        # Only broadcast if state changed (or periodic refresh)
        state_hash = json.dumps(state, sort_keys=True)
        if state_hash != self._last_state.get("hash"):
            self._send_state_message(state)
            self._last_state["hash"] = state_hash
            self._last_state["time"] = time.time()
    
    def _build_state_message(self) -> Dict[str, Any]:
        """Build state message from current system state"""
        # Get active animation
        active_anim = self.animation_service.get_active_animation()
        
        # Build animation state
        animation_state = None
        if active_anim:
            animation_state = {
                "id": self._animation_to_id(active_anim.config.id),
                "speed": active_anim.parameters.get("speed", 1.0),
                "param1": active_anim.parameters.get("param1", 0.0),
                "param2": active_anim.parameters.get("param2", 0.0)
            }
        
        # Build zone states
        zones_state = {}
        for zone in self.zone_service.get_all():
            zone_data = {
                "hue": zone.state.color.to_hue() if zone.state.color else 0,
                "sat": zone.state.color.saturation if hasattr(zone.state.color, 'saturation') else 255,
                "bright": zone.parameters.get("brightness", 255)
            }
            zones_state[zone.config.id.name] = zone_data
        
        return {
            "animation": animation_state,
            "zones": zones_state
        }
    
    def _send_state_message(self, state: Dict[str, Any]):
        """Send state message via UDP multicast"""
        timestamp = time.time()
        payload = json.dumps(state).encode()
        
        # Build message: [type:1][timestamp:8][payload_len:2][payload]
        header = struct.pack(
            ">BdH",
            MessageType.STATE.value,
            timestamp,
            len(payload)
        )
        
        message = header + payload
        self.sock.sendto(message, (self.MULTICAST_GROUP, self.MULTICAST_PORT))
        
        log.debug("State broadcast sent", size=len(message))
    
    def _send_sync_pulse(self):
        """Send time sync pulse"""
        timestamp = time.time()
        message = struct.pack(">Bd", MessageType.SYNC.value, timestamp)
        self.sock.sendto(message, (self.MULTICAST_GROUP, self.MULTICAST_PORT))
    
    # ==================== Event Handlers ====================
    
    def _on_zone_changed(self, event):
        """Handle zone state change - immediate broadcast"""
        # Could trigger immediate state broadcast here
        # For now, regular broadcast loop handles it
        pass
    
    def _on_animation_started(self, event):
        """Handle animation start - immediate broadcast"""
        asyncio.create_task(self._broadcast_full_state())
    
    def _on_animation_stopped(self, event):
        """Handle animation stop - immediate broadcast"""
        asyncio.create_task(self._broadcast_full_state())
    
    # ==================== Helpers ====================
    
    def _animation_to_id(self, animation_id: AnimationID) -> int:
        """Convert AnimationID enum to numeric ID for ESP32"""
        mapping = {
            AnimationID.STATIC: 0,
            AnimationID.RAINBOW: 1,
            AnimationID.BREATHE: 2,
            AnimationID.WAVE: 3,
            AnimationID.FIRE: 4,
            # Add more as needed
        }
        return mapping.get(animation_id, 0)
    
    def send_command(self, command: str, params: Dict[str, Any] = None):
        """Send immediate command to ESP32s (e.g., reboot, config update)"""
        message = struct.pack(">B", MessageType.COMMAND.value)
        payload = json.dumps({
            "command": command,
            "params": params or {}
        }).encode()
        
        message += struct.pack(">H", len(payload))
        message += payload
        
        self.sock.sendto(message, (self.MULTICAST_GROUP, self.MULTICAST_PORT))
        log.info("Command sent", command=command)


# Integration with main_asyncio.py
async def setup_esp32_broadcaster(services) -> ESP32Broadcaster:
    """Factory function for main.py integration"""
    broadcaster = ESP32Broadcaster(
        zone_service=services.zone_service,
        animation_service=services.animation_service,
        event_bus=services.event_bus
    )
    await broadcaster.start()
    return broadcaster
```

---

## Summary & Recommendations

### Key Takeaways

1. **Architecture: Use Hybrid Pattern**
   - RPi: Brain (calculations, UI, storage)
   - ESP32: Muscle (local rendering, sensors)
   - Communication: State, not frames

2. **Protocol: UDP Multicast + NTP**
   - UDP multicast for state broadcast (low latency, scales)
   - NTP for time sync (good enough for LEDs)
   - WebSocket for bidirectional (browser + ESP32 status)

3. **Animations: Deterministic Time-Based**
   - Same time + same params = same output
   - All ESP32s render same frame at same real-world time
   - Resilient to network issues

4. **Synchronization: Application-Level + NTP**
   - NTP for coarse sync (~20ms)
   - Timestamps in messages for fine-tuning
   - Beat-relative for music sync

### Your Next Steps

1. **Phase 1: Basic Integration**
   - Add `ESP32Broadcaster` to Diuna
   - Flash test ESP32 with receiver code
   - Verify multicast works on your network

2. **Phase 2: Animation Porting**
   - Port existing Diuna animations to ESP32
   - Test synchronization accuracy
   - Add deterministic random for effects like fire

3. **Phase 3: Sensors & Features**
   - Add accelerometer for wearable
   - Add BLE for phone control
   - Add local presets for offline mode

4. **Phase 4: Production**
   - OTA updates for ESP32 firmware
   - Device discovery/registration
   - Monitoring dashboard

### Resources

- **FastLED Library:** https://github.com/FastLED/FastLED
- **ESP32 Arduino Core:** https://github.com/espressif/arduino-esp32
- **PlatformIO:** https://platformio.org/ (recommended over Arduino IDE)
- **ESPAsyncWebServer:** For web config on ESP32
- **AsyncMQTTClient:** If you add MQTT later

Good luck with your ESP32 integration! 🚀
