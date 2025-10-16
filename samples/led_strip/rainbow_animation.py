#!/usr/bin/env python3
"""
WS2811/WS2812B ARGB LED Strip - Rainbow Animation
GPIO 18 (PWM pin required for WS281x)

Install required library first:
pip install rpi-ws281x

Wiring:
- LED Strip DIN (Data) → GPIO 18 (PWM0)
- LED Strip +5V → 5V power supply (NOT from Pi if >10 LEDs!)
- LED Strip GND → Common GND (Pi + power supply)
"""
import time
from rpi_ws281x import PixelStrip, Color

# LED strip configuration
LED_COUNT = 30          # Number of LED pixels
LED_PIN = 18            # GPIO pin (must be PWM: 10, 12, 18, 21)
LED_FREQ_HZ = 800000    # LED signal frequency in Hz (800kHz)
LED_DMA = 10           # DMA channel
LED_BRIGHTNESS = 255    # Brightness (0-255)
LED_INVERT = False     # True to invert signal
LED_CHANNEL = 0        # PWM channel

# Create NeoPixel object
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow_cycle(wait_ms=20, iterations=5):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)

def color_wipe(color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)

def theater_chase(color, wait_ms=50, iterations=10):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)

print("WS2811/WS2812B LED Strip Animations")
print(f"LED Count: {LED_COUNT}")
print(f"GPIO Pin: {LED_PIN}")
print("Press Ctrl+C to exit")
print()

try:
    while True:
        print("Rainbow cycle...")
        rainbow_cycle(20, 2)

        print("Color wipe - Red")
        color_wipe(Color(255, 0, 0), 50)

        print("Color wipe - Green")
        color_wipe(Color(0, 255, 0), 50)

        print("Color wipe - Blue")
        color_wipe(Color(0, 0, 255), 50)

        print("Theater chase - White")
        theater_chase(Color(127, 127, 127), 50, 10)

        print("Theater chase - Red")
        theater_chase(Color(127, 0, 0), 50, 10)

except KeyboardInterrupt:
    print("\nStopped")
finally:
    # Turn off all LEDs
    color_wipe(Color(0, 0, 0), 10)
    print("LEDs off")
