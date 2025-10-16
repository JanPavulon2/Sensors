#!/usr/bin/env python3
"""
Working LED strip with BRG color order
"""
import time
from rpi_ws281x import PixelStrip, Color, ws

LED_COUNT = 30       # 20 + 4 pixels
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 128
LED_INVERT = False
LED_CHANNEL = 0
LED_STRIP = ws.WS2811_STRIP_BRG  # BRG color order!

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

def rainbow_cycle(wait_ms=20, iterations=5):
    """Rainbow animation"""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)

def color_wipe(color, wait_ms=50):
    """Wipe color across display"""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)

def theater_chase(color, wait_ms=50, iterations=10):
    """Theater chase animation"""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)

print(f"WS2811 LED Strip - {LED_COUNT} pixels (BRG color order)")
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

except KeyboardInterrupt:
    print("\nStopped")
finally:
    color_wipe(Color(0, 0, 0), 10)
    print("LEDs off")
