# Keyboard Input System — Overview (Short)

This document describes the **keyboard input subsystem** as a whole.
It covers architecture, adapter selection, runtime flow, and developer-facing behavior.

The system is designed to work across platforms and environments, with graceful degradation.

---

## Components

### IKeyboardAdapter (Base)

Defines the common contract for all keyboard adapters.

Responsibilities:

* expose `run()` coroutine
* publish keyboard events to EventBus
* handle its own lifecycle (startup, cancellation, cleanup)

The adapter **does not** manage task scheduling.

---

### EvdevKeyboardAdapter (Linux / Physical)

Used when running on Linux with access to `/dev/input`.

Features:

* true key-down / key-up events
* reliable modifier tracking (SHIFT, CTRL, ALT)
* no escape sequences

This is the **highest-fidelity** keyboard backend.

---

### StdinKeyboardAdapter (Terminal)

Used when evdev is unavailable and STDIN is a TTY.

Features:

* works over SSH and local terminals
* async-friendly
* parses escape sequences (arrow keys)

Limitations:

* byte-based input
* no key-up events
* modifiers inferred, not tracked

---

### DummyKeyboardAdapter (Fallback)

Used when no keyboard input is possible.

Behavior:

* does nothing
* keeps the system running

---

### Keyboard Adapter Factory

Selects the best available adapter at runtime:

Priority order:

1. Evdev
2. STDIN
3. Dummy

Selection is based on environment capability detection.

---

## Runtime Flow

1. Runtime creates adapter via factory
2. Runtime schedules `adapter.run()` as an asyncio task
3. Adapter reads input and publishes events
4. Events are consumed elsewhere in the system

---

## Known Issue (STDIN): "Delay of 1"

Arrow keys may appear logged **one key late**.

This is a known limitation of STDIN byte buffering and escape sequence timing.
See the detailed documentation for explanation.


