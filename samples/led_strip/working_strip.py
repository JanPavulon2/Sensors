#!/usr/bin/env python3
"""
Working LED strip with correct GRB color order
"""
import time
from rpi_ws281x import PixelStrip, Color, ws

LED_COUNT = 24       # Your working strips
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 128
LED_INVERT = False
LED_CHANNEL = 0
LED_STRIP = ws.SK6812_STRIP_GRBW  # GRB color order!

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
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
    """Set all to color"""
    color = Color(r, g, b)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

print(f"WS2811 with GRB color order - {LED_COUNT} pixels")
print()

try:
    # Test colors
    print("RED")
    set_all(255, 0, 0)
    time.sleep(2)

    print("GREEN")
    set_all(0, 255, 0)
    time.sleep(2)

    print("BLUE")
    set_all(0, 0, 255)
    time.sleep(2)

    print("Rainbow...")
    for _ in range(3):
        rainbow_cycle(20)

except KeyboardInterrupt:
    print("\nStopped")
finally:
    set_all(0, 0, 0)
    print("LEDs off")
