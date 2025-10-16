#!/usr/bin/env python3
"""
LED Strip Tester
Test LED strip segments by touching test pads

Hardware:
- 3x pogo pins/probes connected to:
  - Probe 1: +5V or +12V (from PSU)
  - Probe 2: DIN (from GPIO 18)
  - Probe 3: GND (common GND)

Usage:
1. Set LED_COUNT to max LEDs you want to test
2. Run this script
3. Touch probes to LED strip cut pads
4. LEDs from touch point to end should light up
5. If they don't = strip broken at that point
"""
import time
from rpi_ws281x import PixelStrip, Color, ws

LED_COUNT = 20     # Max LEDs to test (set high)
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 128
LED_INVERT = False
LED_CHANNEL = 0
LED_STRIP = ws.WS2811_STRIP_BRG  # Change to your strip type

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
strip.begin()

def test_pattern():
    """Rainbow pattern for testing"""
    colors = [
        Color(255, 0, 0),    # Red
        Color(0, 255, 0),    # Green
        Color(0, 0, 255),    # Blue
        Color(255, 255, 0),  # Yellow
        Color(0, 255, 255),  # Cyan
        Color(255, 0, 255),  # Magenta
    ]

    for i in range(LED_COUNT):
        strip.setPixelColor(i, colors[i % len(colors)])
    strip.show()

def clear():
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

print("LED Strip Tester")
print("=" * 40)
print("Touch probes to LED strip pads:")
print("  Probe 1: +5V or +12V (power)")
print("  Probe 2: DIN (data from GPIO 18)")
print("  Probe 3: GND (ground)")
print()
print("LEDs should light up from touch point")
print("If they don't = strip broken before that point")
print()
print("Press Ctrl+C to exit")
print("=" * 40)

try:
    while True:
        test_pattern()
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopped")
finally:
    # Clear all LEDs (send black color)
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    time.sleep(0.1)  # Make sure command is sent
    print("All LEDs off")
