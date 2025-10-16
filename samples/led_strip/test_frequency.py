#!/usr/bin/env python3
"""
Test different frequencies for flickering strip
"""
import time
from rpi_ws281x import PixelStrip, Color, ws

LED_COUNT = 24
LED_PIN = 18
LED_FREQ_HZ = 400000  # Try 400kHz instead of 800kHz
LED_DMA = 10
LED_BRIGHTNESS = 128
LED_INVERT = False
LED_CHANNEL = 0
LED_STRIP = ws.WS2811_STRIP_BRG

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
strip.begin()

def set_all(r, g, b):
    color = Color(r, g, b)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

print(f"Testing {LED_FREQ_HZ}Hz frequency")

try:
    print("Smooth fade RED to BLUE")
    for i in range(256):
        set_all(255-i, 0, i)
        time.sleep(0.01)

    print("Does it flicker? (y/n)")

except KeyboardInterrupt:
    print("\nStopped")
finally:
    set_all(0, 0, 0)
