#!/usr/bin/env python3
"""
Test dual GPIO - Strip on GPIO 18, Preview on GPIO 19

IMPORTANT: RPi has 2 PWM channels:
  - PWM Channel 0: GPIO 12 or 18
  - PWM Channel 1: GPIO 13 or 19

Configuration:
  - Strip: GPIO 18 (PWM Channel 0) - BRG color order
  - Preview: GPIO 19 (PWM Channel 1) - RGB color order

NOTE: GPIO 19 was BTN4 - button needs to be moved to different pin (e.g. GPIO 22)
"""

import time
from rpi_ws281x import PixelStrip, Color, ws

# Main Strip - GPIO 18 (PWM Channel 0, RBG color order)
STRIP_PIN = 18
STRIP_COUNT = 14  # 42 physical LEDs / 3
strip = PixelStrip(STRIP_COUNT, STRIP_PIN, 800000, 10, False, 32, 0, ws.WS2811_STRIP_RBG)

# Preview Panel - GPIO 19 (PWM Channel 1)
# Testing different color orders to find the right one
PREVIEW_PIN = 19
PREVIEW_COUNT = 8
# Try GRB order (most common for WS2812B/CJMCU)
preview = PixelStrip(PREVIEW_COUNT, PREVIEW_PIN, 800000, 10, False, 32, 1, ws.WS2811_STRIP_GRB)

print("Initializing dual GPIO setup...")
print("Strip (GPIO 18, PWM Ch 0): RBG order")
print("Preview (GPIO 19, PWM Ch 1): GRB order")
print()

# Initialize
preview.begin()
strip.begin()

print("Testing colors...")
print("Preview should show RED")
print("Strip should show GREEN")
print()

try:
    # Preview - RED (RGB order)
    for i in range(PREVIEW_COUNT):
        preview.setPixelColor(i, Color(255, 0, 0))  # RGB: R=255, G=0, B=0
    preview.show()

    # Strip - GREEN
    # Color() always takes (R, G, B) but strip expects RBG
    # For green: want R=0, B=0, G=255
    # Send Color(R=0, G=255, B=0) → strip reads R=0, B=0, G=255
    for i in range(STRIP_COUNT):
        strip.setPixelColor(i, Color(0, 255, 0))  # GREEN in RBG
    strip.show()

    print("LEDs set! Press Ctrl+C to exit")

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nClearing...")

    for i in range(PREVIEW_COUNT):
        preview.setPixelColor(i, Color(0, 0, 0))
    preview.show()

    for i in range(STRIP_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    print("Done!")
