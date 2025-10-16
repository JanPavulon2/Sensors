#!/usr/bin/env python3
"""
Test all color orders to find the right one
"""
import time
from rpi_ws281x import PixelStrip, Color, ws

LED_COUNT = 24
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 128
LED_INVERT = False
LED_CHANNEL = 0

# All possible color orders
STRIP_TYPES = [
    ("RGB", ws.WS2811_STRIP_RGB),
    ("RBG", ws.WS2811_STRIP_RBG),
    ("GRB", ws.WS2811_STRIP_GRB),
    ("GBR", ws.WS2811_STRIP_GBR),
    ("BRG", ws.WS2811_STRIP_BRG),
    ("BGR", ws.WS2811_STRIP_BGR),
]

def test_strip_type(name, strip_type):
    print(f"\n=== Testing {name} ===")

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                       LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, strip_type)
    strip.begin()

    # Red
    print(f"{name}: Setting RED")
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(255, 0, 0))
    strip.show()
    time.sleep(3)

    # Green
    print(f"{name}: Setting GREEN")
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 255, 0))
    strip.show()
    time.sleep(3)

    # Blue
    print(f"{name}: Setting BLUE")
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 255))
    strip.show()
    time.sleep(3)

    # Off
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

print("Color Order Tester")
print("Watch the LEDs and note which order gives correct colors:")
print("RED should be RED, GREEN should be GREEN, BLUE should be BLUE")
print()

try:
    for name, strip_type in STRIP_TYPES:
        test_strip_type(name, strip_type)
        time.sleep(1)

    print("\n\nWhich one was correct? Use that in your code!")

except KeyboardInterrupt:
    print("\nStopped")
