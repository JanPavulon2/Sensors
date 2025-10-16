#!/usr/bin/env python3
"""
LED Animation Library - 15 presets
Subtle and flashy animations for WS2811/WS2812B strips
"""
import time
from rpi_ws281x import PixelStrip, Color
import math

class LEDAnimations:
    def __init__(self, strip):
        self.strip = strip
        self.num_pixels = strip.numPixels()

    # ===== HELPER FUNCTIONS =====
    def clear(self):
        """Turn off all LEDs"""
        for i in range(self.num_pixels):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()

    def wheel(self, pos):
        """Generate rainbow colors across 0-255 positions"""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)

    # ===== SUBTLE ANIMATIONS =====
    def breathe(self, color, duration=3, cycles=3):
        """
        1. Breathe - gentle fade in/out
        Subtle, calming effect
        """
        r, g, b = color
        steps = 100

        for _ in range(cycles):
            # Fade in
            for i in range(steps):
                brightness = i / steps
                for pixel in range(self.num_pixels):
                    self.strip.setPixelColor(pixel, Color(
                        int(r * brightness),
                        int(g * brightness),
                        int(b * brightness)
                    ))
                self.strip.show()
                time.sleep(duration / (2 * steps))

            # Fade out
            for i in range(steps, -1, -1):
                brightness = i / steps
                for pixel in range(self.num_pixels):
                    self.strip.setPixelColor(pixel, Color(
                        int(r * brightness),
                        int(g * brightness),
                        int(b * brightness)
                    ))
                self.strip.show()
                time.sleep(duration / (2 * steps))

    def static_color(self, color, duration=5):
        """
        2. Static Color - solid color, no animation
        Most subtle, lowest power
        """
        r, g, b = color
        for i in range(self.num_pixels):
            self.strip.setPixelColor(i, Color(r, g, b))
        self.strip.show()
        time.sleep(duration)

    def slow_pulse(self, color, duration=10):
        """
        3. Slow Pulse - very slow breathe (10s cycle)
        Background ambient effect
        """
        self.breathe(color, duration=duration, cycles=1)

    def gradient_static(self, color1, color2, duration=5):
        """
        4. Gradient Static - smooth color transition across strip
        Subtle, no movement
        """
        r1, g1, b1 = color1
        r2, g2, b2 = color2

        for i in range(self.num_pixels):
            ratio = i / self.num_pixels
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            self.strip.setPixelColor(i, Color(r, g, b))
        self.strip.show()
        time.sleep(duration)

    def twinkle(self, color, duration=10, density=0.1):
        """
        5. Twinkle - random pixels gently sparkle
        Subtle, starfield effect
        """
        import random
        r, g, b = color
        end_time = time.time() + duration

        while time.time() < end_time:
            # Random pixels at random brightness
            for i in range(self.num_pixels):
                if random.random() < density:
                    brightness = random.uniform(0.3, 1.0)
                    self.strip.setPixelColor(i, Color(
                        int(r * brightness),
                        int(g * brightness),
                        int(b * brightness)
                    ))
                else:
                    self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.show()
            time.sleep(0.1)

    # ===== MEDIUM ANIMATIONS =====
    def color_wipe(self, color, wait_ms=50):
        """
        6. Color Wipe - fill strip pixel by pixel
        Classic smooth effect
        """
        r, g, b = color
        for i in range(self.num_pixels):
            self.strip.setPixelColor(i, Color(r, g, b))
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def rainbow_cycle(self, wait_ms=20, iterations=1):
        """
        7. Rainbow Cycle - smooth rainbow across strip
        Classic rainbow effect
        """
        for j in range(256 * iterations):
            for i in range(self.num_pixels):
                pixel_index = (i * 256 // self.num_pixels) + j
                self.strip.setPixelColor(i, self.wheel(pixel_index & 255))
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def scanner(self, color, width=4, speed=50):
        """
        8. Scanner (Larson Scanner) - KITT/Cylon eye effect
        Back and forth sweep
        """
        r, g, b = color

        # Sweep right
        for pos in range(self.num_pixels - width):
            self.clear()
            for i in range(width):
                self.strip.setPixelColor(pos + i, Color(r, g, b))
            self.strip.show()
            time.sleep(speed / 1000.0)

        # Sweep left
        for pos in range(self.num_pixels - width, -1, -1):
            self.clear()
            for i in range(width):
                self.strip.setPixelColor(pos + i, Color(r, g, b))
            self.strip.show()
            time.sleep(speed / 1000.0)

    def comet(self, color, tail_length=8, speed=30):
        """
        9. Comet - moving pixel with fading tail
        Smooth shooting star effect
        """
        r, g, b = color

        for pos in range(self.num_pixels + tail_length):
            self.clear()
            # Draw comet with fading tail
            for i in range(tail_length):
                pixel_pos = pos - i
                if 0 <= pixel_pos < self.num_pixels:
                    brightness = (tail_length - i) / tail_length
                    self.strip.setPixelColor(pixel_pos, Color(
                        int(r * brightness),
                        int(g * brightness),
                        int(b * brightness)
                    ))
            self.strip.show()
            time.sleep(speed / 1000.0)

    def wave(self, color, wavelength=10, speed=50, cycles=3):
        """
        10. Wave - sine wave brightness modulation
        Smooth flowing effect
        """
        r, g, b = color

        for cycle in range(cycles * wavelength):
            for i in range(self.num_pixels):
                brightness = (math.sin((i + cycle) * 2 * math.pi / wavelength) + 1) / 2
                self.strip.setPixelColor(i, Color(
                    int(r * brightness),
                    int(g * brightness),
                    int(b * brightness)
                ))
            self.strip.show()
            time.sleep(speed / 1000.0)

    # ===== FLASHY ANIMATIONS =====
    def strobe(self, color, flashes=10, speed=100):
        """
        11. Strobe - rapid on/off flashing
        High energy effect
        """
        r, g, b = color

        for _ in range(flashes):
            for i in range(self.num_pixels):
                self.strip.setPixelColor(i, Color(r, g, b))
            self.strip.show()
            time.sleep(speed / 1000.0)

            self.clear()
            time.sleep(speed / 1000.0)

    def theater_chase(self, color, iterations=10, speed=100):
        """
        12. Theater Chase - every 3rd pixel lights up, rotating
        Classic marquee effect
        """
        r, g, b = color

        for j in range(iterations):
            for q in range(3):
                for i in range(0, self.num_pixels, 3):
                    self.strip.setPixelColor(i + q, Color(r, g, b))
                self.strip.show()
                time.sleep(speed / 1000.0)

                for i in range(0, self.num_pixels, 3):
                    self.strip.setPixelColor(i + q, Color(0, 0, 0))

    def rainbow_chase(self, speed=50):
        """
        13. Rainbow Chase - theater chase with rainbow colors
        Colorful moving effect
        """
        for j in range(256):
            for q in range(3):
                for i in range(0, self.num_pixels, 3):
                    self.strip.setPixelColor(i + q, self.wheel((i + j) % 255))
                self.strip.show()
                time.sleep(speed / 1000.0)

                for i in range(0, self.num_pixels, 3):
                    self.strip.setPixelColor(i + q, Color(0, 0, 0))

    def fire(self, duration=10, cooling=55, sparking=120):
        """
        14. Fire - flickering fire effect
        Organic, random movement
        """
        import random
        heat = [0] * self.num_pixels
        end_time = time.time() + duration

        while time.time() < end_time:
            # Cool down every cell
            for i in range(self.num_pixels):
                cooldown = random.randint(0, ((cooling * 10) // self.num_pixels) + 2)
                heat[i] = max(0, heat[i] - cooldown)

            # Heat from each cell drifts up
            for k in range(self.num_pixels - 1, 1, -1):
                heat[k] = (heat[k - 1] + heat[k - 2] + heat[k - 2]) // 3

            # Randomly ignite new sparks
            if random.randint(0, 255) < sparking:
                y = random.randint(0, 7)
                heat[y] = min(255, heat[y] + random.randint(160, 255))

            # Convert heat to LED colors
            for j in range(self.num_pixels):
                t192 = round((heat[j] / 255.0) * 191)
                heatramp = t192 & 0x3F
                heatramp <<= 2

                if t192 > 0x80:
                    color = Color(255, 255, heatramp)
                elif t192 > 0x40:
                    color = Color(255, heatramp, 0)
                else:
                    color = Color(heatramp, 0, 0)

                self.strip.setPixelColor(j, color)

            self.strip.show()
            time.sleep(0.02)

    def color_fade_cycle(self, colors, fade_time=2):
        """
        15. Color Fade Cycle - smooth fade between multiple colors
        Gentle color transitions
        """
        steps = 100

        for i in range(len(colors)):
            color1 = colors[i]
            color2 = colors[(i + 1) % len(colors)]

            r1, g1, b1 = color1
            r2, g2, b2 = color2

            for step in range(steps):
                ratio = step / steps
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)

                for pixel in range(self.num_pixels):
                    self.strip.setPixelColor(pixel, Color(r, g, b))
                self.strip.show()
                time.sleep(fade_time / steps)


# ===== DEMO / TEST =====
if __name__ == "__main__":
    from rpi_ws281x import ws

    LED_COUNT = 8
    LED_PIN = 18
    LED_BRIGHTNESS = 32  # Low brightness for subtle effects

    strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False,
                       LED_BRIGHTNESS, 0, ws.WS2811_STRIP_BRG)
    strip.begin()

    animations = LEDAnimations(strip)

    print("LED Animation Demo - 15 Presets")
    print("Press Ctrl+C to stop")

    try:
        while True:
            print("\n1. Breathe (red)")
            animations.breathe((255, 0, 0), duration=2, cycles=2)

            print("2. Static Color (blue)")
            animations.static_color((0, 0, 255), duration=3)

            print("3. Slow Pulse (green)")
            animations.slow_pulse((0, 255, 0), duration=5)

            print("4. Gradient (red to blue)")
            animations.gradient_static((255, 0, 0), (0, 0, 255), duration=3)

            print("5. Twinkle (white)")
            animations.twinkle((255, 255, 255), duration=5)

            print("6. Color Wipe (purple)")
            animations.color_wipe((128, 0, 128))
            animations.clear()

            print("7. Rainbow Cycle")
            animations.rainbow_cycle(wait_ms=10, iterations=1)

            print("8. Scanner (cyan)")
            animations.scanner((0, 255, 255), speed=30)

            print("9. Comet (yellow)")
            animations.comet((255, 255, 0), speed=20)

            print("10. Wave (magenta)")
            animations.wave((255, 0, 255), wavelength=8, speed=30)

            print("11. Strobe (white)")
            animations.strobe((255, 255, 255), flashes=5, speed=50)

            print("12. Theater Chase (red)")
            animations.theater_chase((255, 0, 0), iterations=5)

            print("13. Rainbow Chase")
            animations.rainbow_chase(speed=30)

            print("14. Fire")
            animations.fire(duration=5)

            print("15. Color Fade Cycle")
            animations.color_fade_cycle([
                (255, 0, 0),    # Red
                (0, 255, 0),    # Green
                (0, 0, 255),    # Blue
                (255, 255, 0)   # Yellow
            ], fade_time=3)

            animations.clear()
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopped")
        animations.clear()
