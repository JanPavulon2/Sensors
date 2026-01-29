# Keyboard Input System — Detailed Documentation

This document provides a **complete technical description** of the keyboard input subsystem.
It is intended for developers extending, debugging, or integrating keyboard input.

---

## Design Goals

* platform independence
* async compatibility
* graceful degradation
* explicit responsibility boundaries

The system prefers **correctness over cleverness**.

---

## Architecture Overview

Keyboard input is implemented using a **strategy pattern**:

* one common interface (`IKeyboardAdapter`)
* multiple concrete adapters
* a runtime factory that selects the best adapter

The runtime owns task scheduling.
Adapters own input parsing and cleanup.

---

## IKeyboardAdapter (Base Contract)

Required behavior:

* expose `async def run() -> None`
* block until cancelled
* publish `KeyboardKeyPressEvent`
* restore any modified system state on exit

Adapters must:

* handle `asyncio.CancelledError`
* not swallow cancellation

---

## EvdevKeyboardAdapter

### Environment

* Linux only
* requires access to `/dev/input/event*`

### Characteristics

* event-driven (kernel-level)
* no buffering ambiguity
* precise modifier state tracking

### Data Model

* separate key-down / key-up events
* modifier state updated explicitly

This adapter is considered **authoritative**.

---

## StdinKeyboardAdapter

### Environment

* Unix terminals
* SSH sessions
* VS Code terminal

### Input Model

STDIN delivers **bytes**, not keys.

Examples:

* `a` → `0x61`
* `A` → `0x41`
* UP arrow → `ESC [ A`

There is no guarantee of atomic delivery.

---

### Escape Sequences

Arrow keys and function keys are encoded as multi-byte sequences.

Common arrow keys:

* `ESC [ A` → UP
* `ESC [ B` → DOWN
* `ESC [ C` → RIGHT
* `ESC [ D` → LEFT

These bytes may arrive:

* together
* partially
* with timing gaps

---

### The "Delay of 1" Problem (Root Cause)

Observed behavior:

* pressing key N logs key N-1

Why this happens:

* input is read one byte at a time
* escape sequence completion is detected late
* buffer parsing emits an event only after the *next* read

This is not a bug in asyncio.
This is not a race condition.
This is a **semantic mismatch** between:

* byte streams (STDIN)
* event streams (keyboard)

STDIN has no framing.

---

### Why It Cannot Be Fully Fixed

Without:

* blocking reads
* OS-level key events
* or terminal-specific libraries (e.g. curses)

it is impossible to guarantee zero-latency parsing of escape sequences.

Any solution is a trade-off between:

* responsiveness
* correctness
* complexity

---

### Practical Implications

STDIN adapter is suitable for:

* development
* debugging
* simple control schemes

It is **not** suitable for:

* real-time input
* precise key timing
* games or reactive UIs

---

## DummyKeyboardAdapter

Purpose:

* keep the system running
* avoid conditional logic elsewhere

Behavior:

* never emits events
* blocks until cancelled

---

## Keyboard Adapter Factory

Responsibilities:

* detect environment capabilities
* select best adapter
* log selection and fallbacks

It does **not**:

* start tasks
* manage lifetimes

---

## Runtime Integration

Correct usage:

* runtime calls factory
* runtime schedules `adapter.run()`
* runtime tracks and cancels task

Adapters must never self-schedule.

---

## Summary

* evdev is precise and preferred
* stdin is lossy and best-effort
* dummy is safe fallback

The system is designed to fail **softly**, not silently.
