#!/usr/bin/env python3
"""
WS2811/WS2812B - Simple color control
GPIO 18
"""
import time
from rpi_ws281x import PixelStrip, Color

# Configuration
LED_COUNT = 42
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255  # Lower brightness (0-255)
LED_INVERT = False
LED_CHANNEL = 0

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def set_all_color(r, g, b):
    """Set all LEDs to same color (RGB 0-255)"""
    color = Color(r, g, b)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

def clear():
    """Turn off all LEDs"""
    set_all_color(0, 0, 0)

print("WS2811 Simple Color Control")
print(f"{LED_COUNT} LEDs on GPIO {LED_PIN}")
print()

try:
    # Demo colors
    colors = [
        ("Red", 255, 0, 0),
        ("Green", 0, 255, 0),
        ("Blue", 0, 0, 255),
        ("Yellow", 255, 255, 0),
        ("Cyan", 0, 255, 255),
        ("Magenta", 255, 0, 255),
        ("White", 255, 255, 255),
    ]

    for name, r, g, b in colors:
        print(f"{name} ({r}, {g}, {b})")
        set_all_color(r, g, b)
        time.sleep(1)

    # Interactive mode
    print("\nInteractive mode")
    print("Enter RGB values (0-255) or 'q' to quit")

    while True:
        cmd = input("\nR G B (e.g., '255 0 0'): ")

        if cmd.lower() == 'q':
            break

        try:
            r, g, b = map(int, cmd.split())
            if all(0 <= c <= 255 for c in [r, g, b]):
                set_all_color(r, g, b)
                print(f"Set to RGB({r}, {g}, {b})")
            else:
                print("Values must be 0-255")
        except:
            print("Invalid format. Use: R G B (e.g., '255 0 0')")

except KeyboardInterrupt:
    print("\nStopped")
finally:
    clear()
    print("LEDs off")
