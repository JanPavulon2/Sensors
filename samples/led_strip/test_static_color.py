#!/usr/bin/env python3
"""
Static color test - no animation
Check if all strips light up
"""
import time
from rpi_ws281x import PixelStrip, Color

# Configuration
LED_COUNT = 2       # 20 + 4 + 3 = 27 pixels
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 128
LED_INVERT = False
LED_CHANNEL = 0

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def set_all_color(r, g, b):
    """Set all LEDs to one color"""
    color = Color(r, g, b)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

def clear():
    """Turn off all LEDs"""
    set_all_color(0, 0, 0)

print(f"Testing {LED_COUNT} pixels on GPIO {LED_PIN}")
print("Testing colors...")
print()

try:
    # Test 1: All red
    print("All RED (5 sec)")
    set_all_color(255, 0, 0)
    time.sleep(7)

    # Test 2: All green
    print("All GREEN (5 sec)")
    set_all_color(0, 255, 0)
    time.sleep(7)

    # Test 3: All blue
    print("All BLUE (5 sec)")
    set_all_color(0, 0, 255)
    time.sleep(7)

    # Test 4: White
    print("All WHITE (5 sec)")
    set_all_color(255, 255, 255)
    time.sleep(5)

    # Test 5: Pixel by pixel
    print("\nPixel by pixel test (red)...")
    clear()
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(255, 0, 0))
        strip.show()
        print(f"Pixel {i} ON")
        time.sleep(0.5)

    print("\nTest completed!")

except KeyboardInterrupt:
    print("\nStopped")
finally:
    clear()
    print("LEDs off")
