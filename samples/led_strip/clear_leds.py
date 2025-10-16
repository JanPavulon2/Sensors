#!/usr/bin/env python3
"""
Clear all LEDs - force turn off
"""
from rpi_ws281x import PixelStrip, Color, ws

LED_COUNT = 8
LED_PIN = 18

strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False, 128, 0, ws.WS2811_STRIP_BRG)
strip.begin()

# Turn off all LEDs
for i in range(LED_COUNT):
    strip.setPixelColor(i, Color(0, 0, 0))
strip.show()

print("LEDs cleared")
