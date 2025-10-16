#!/usr/bin/env python3
"""
Example 4: Reusable MOSFET Controller Class
This class can be imported and used in your projects
"""
import RPi.GPIO as GPIO
import time


class MOSFETController:
    """
    A reusable class for controlling devices via MOSFET

    Features:
    - Simple ON/OFF control
    - PWM brightness control (0-100%)
    - Fade in/out animations
    """

    def __init__(self, pin, pwm_frequency=1000):
        """
        Initialize MOSFET controller

        Args:
            pin: GPIO pin number (BCM mode)
            pwm_frequency: PWM frequency in Hz (default 1000)
        """
        self.pin = pin
        self.frequency = pwm_frequency
        self.pwm = None

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)

    def on(self):
        """Turn ON at 100%"""
        GPIO.output(self.pin, GPIO.HIGH)

    def off(self):
        """Turn OFF"""
        GPIO.output(self.pin, GPIO.LOW)

    def set_brightness(self, percent):
        """
        Set brightness (0-100%)

        Args:
            percent: Brightness level 0-100
        """
        if self.pwm is None:
            self.pwm = GPIO.PWM(self.pin, self.frequency)
            self.pwm.start(0)

        percent = max(0, min(100, percent))  # Clamp 0-100
        self.pwm.ChangeDutyCycle(percent)

    def fade_in(self, duration=1.0, steps=50):
        """
        Smooth fade in

        Args:
            duration: Duration in seconds
            steps: Number of steps (more = smoother)
        """
        if self.pwm is None:
            self.pwm = GPIO.PWM(self.pin, self.frequency)
            self.pwm.start(0)

        delay = duration / steps
        for i in range(steps + 1):
            duty = (i / steps) * 100
            self.pwm.ChangeDutyCycle(duty)
            time.sleep(delay)

    def fade_out(self, duration=1.0, steps=50):
        """
        Smooth fade out

        Args:
            duration: Duration in seconds
            steps: Number of steps (more = smoother)
        """
        if self.pwm is None:
            return

        delay = duration / steps
        for i in range(steps, -1, -1):
            duty = (i / steps) * 100
            self.pwm.ChangeDutyCycle(duty)
            time.sleep(delay)

    def cleanup(self):
        """Cleanup GPIO (call this when done)"""
        if self.pwm:
            self.pwm.stop()
        GPIO.cleanup(self.pin)


# USAGE EXAMPLE:
if __name__ == "__main__":
    led = MOSFETController(pin=17)

    try:
        # Test 1: ON/OFF
        print("Test ON/OFF")
        led.on()
        time.sleep(2)
        led.off()
        time.sleep(1)

        # Test 2: Brightness
        print("Test brightness 50%")
        led.set_brightness(50)
        time.sleep(2)

        # Test 3: Fade
        print("Test fade in/out")
        led.fade_in(duration=2)
        time.sleep(1)
        led.fade_out(duration=2)

        # Test 4: Different brightness levels
        print("Test different brightness levels")
        for brightness in [25, 50, 75, 100]:
            print(f"Brightness: {brightness}%")
            led.set_brightness(brightness)
            time.sleep(1)

        led.off()

    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        led.cleanup()
