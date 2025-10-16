#!/usr/bin/env python3
"""
Test GRB color order (some WS2811 use GRB instead of RGB)
"""
import time
from rpi_ws281x import PixelStrip, Color

LED_COUNT = 24       # Only working strips (20 + 4)
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 128
LED_INVERT = False
LED_CHANNEL = 0

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def set_all_grb(g, r, b):
    """Set all LEDs - using GRB order instead of RGB"""
    color = Color(g, r, b)  # GRB order!
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

def clear():
    set_all_grb(0, 0, 0)

print(f"Testing GRB color order on {LED_COUNT} pixels")
print()

try:
    print("RED (using GRB order)")
    set_all_grb(0, 255, 0)  # G=0, R=255, B=0
    time.sleep(1)

    print("GREEN (using GRB order)")
    set_all_grb(255, 0, 0)  # G=255, R=0, B=0
    time.sleep(3)

    print("BLUE (using GRB order)")
    set_all_grb(0, 0, 255)  # G=0, R=0, B=255
    time.sleep(3)

    print("WHITE (using GRB order)")
    set_all_grb(255, 255, 255)
    time.sleep(3)

    print("\nIf colors are correct now, your strip is GRB!")

except KeyboardInterrupt:
    print("\nStopped")
finally:
    clear()
    print("LEDs off")
