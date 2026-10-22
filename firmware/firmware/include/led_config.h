#pragma once

// FALLBACK output configuration only.
//
// What is actually wired to this node is pushed by the host as a "node.config"
// command and stored in NVS - see applyOutputConfig()/loadOutputConfig() in
// main.cpp. These values are used only on a board that has never been
// configured, so an unprovisioned ESP32 still lights up instead of sitting dark.
//
// Change the rig in the UI (PUT /api/v1/rig/...), not here.

// Set to 1 if a board should default to an addressable strip before the host
// has ever configured it. Leave at 0 to default to the single MOSFET-dimmed
// output on FALLBACK_MOSFET_PIN.
#define USE_ADDRESSABLE_STRIP 0

// Fallback GPIO for the single MOSFET-dimmed output (analog PWM path).
#define FALLBACK_MOSFET_PIN 23

// Fallback data pin and pixel count for the addressable path. FastLED needs
// its pin at compile time, so the pin must be one of those listed in
// beginAddressableOutput() in main.cpp (currently 4, 5, 16, 18).
#define LED_STRIP_DATA_PIN 4
#define LED_STRIP_PIXEL_COUNT 30
