#!/usr/bin/env python3
"""
Example 2: PWM - LED Dimming
PWM (Pulse Width Modulation) allows controlling LED brightness
by rapidly switching it ON and OFF
"""
import RPi.GPIO as GPIO
import time

PIN = 17
FREQUENCY = 1000  # 1kHz

# Configuration
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

# Create PWM object
pwm = GPIO.PWM(PIN, FREQUENCY)
pwm.start(0)  # Start with 0% duty cycle

try:
    while True:
        # Fade in (0% -> 100%)
        print("Fading in...")
        for duty in range(0, 101, 5):
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.05)

        # Fade out (100% -> 0%)
        print("Fading out...")
        for duty in range(100, -1, -5):
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopped")
finally:
    pwm.stop()
    GPIO.cleanup()
