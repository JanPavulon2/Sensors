#!/usr/bin/env python3
"""
WS2811 12V LED Strip with MOSFET Level Shifter
Uses IRLZ44N as signal inverter/level shifter

IMPORTANT: MOSFET inverts signal, so LED_INVERT = True!

Wiring:
- GPIO 18 → 10kΩ resistor → MOSFET Gate
- 5V (external) → 1kΩ resistor → MOSFET Drain → LED DIN
- MOSFET Source → GND
- LED +12V → 12V PSU (+)
- LED GND → Common GND (Pi + PSU)
"""
import time
from rpi_ws281x import PixelStrip, Color

# LED strip configuration
LED_COUNT = 30          # Number of LEDs
LED_PIN = 18            # GPIO pin
LED_FREQ_HZ = 800000    # 800kHz
LED_DMA = 10
LED_BRIGHTNESS = 200    # 0-255
LED_INVERT = True       # TRUE because MOSFET inverts signal!
LED_CHANNEL = 0

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def wheel(pos):
    """Generate rainbow colors"""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow_cycle(wait_ms=20):
    """Rainbow animation"""
    for j in range(256):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)

def set_all(r, g, b):
    """Set all LEDs to one color"""
    color = Color(r, g, b)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

print("WS2811 12V with MOSFET Level Shifter")
print(f"LEDs: {LED_COUNT}, GPIO: {LED_PIN}")
print(f"Signal INVERTED: {LED_INVERT}")
print()

try:
    # Test colors
    print("Red")
    set_all(255, 0, 0)
    time.sleep(2)

    print("Green")
    set_all(0, 255, 0)
    time.sleep(2)

    print("Blue")
    set_all(0, 0, 255)
    time.sleep(2)

    print("Rainbow cycle...")
    for _ in range(3):
        rainbow_cycle(20)

    print("Done!")

except KeyboardInterrupt:
    print("\nStopped")
finally:
    set_all(0, 0, 0)
    print("LEDs off")
