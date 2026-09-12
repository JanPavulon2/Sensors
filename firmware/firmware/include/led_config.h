#pragma once

// Set to 1 once a real WS2812B/WS2811 addressable strip is wired to
// LED_STRIP_DATA_PIN. Until then, leave at 0 to drive the original
// single MOSFET-dimmed LED (MOSFET_PIN in main.cpp) instead - same
// zone.state/identify commands, just a different physical output.
#define USE_ADDRESSABLE_STRIP 0

// Data pin and pixel count for this node's addressable LED strip. Differs
// per physical device, so adjust before flashing a new ESP32. Only used
// when USE_ADDRESSABLE_STRIP is 1.
#define LED_STRIP_DATA_PIN 4
#define LED_STRIP_PIXEL_COUNT 30
