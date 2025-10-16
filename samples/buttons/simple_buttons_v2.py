#!/usr/bin/env python3
"""
Simple button reading with edge detection (single press)
GPIO 16, 20, 21
"""
import RPi.GPIO as GPIO
import time

BUTTON_1 = 16
BUTTON_2 = 20
BUTTON_3 = 21

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Track previous states
prev_btn1 = GPIO.HIGH
prev_btn2 = GPIO.HIGH
prev_btn3 = GPIO.HIGH

print("Button tester (single press detection)")
print("Press buttons on GPIO 16, 20, 21")
print("Press Ctrl+C to exit")

try:
    while True:
        # Read current states
        btn1 = GPIO.input(BUTTON_1)
        btn2 = GPIO.input(BUTTON_2)
        btn3 = GPIO.input(BUTTON_3)

        # Detect falling edge (HIGH -> LOW = button just pressed)
        if prev_btn1 == GPIO.HIGH and btn1 == GPIO.LOW:
            print("Button 1 (GPIO 16) clicked!")

        if prev_btn2 == GPIO.HIGH and btn2 == GPIO.LOW:
            print("Button 2 (GPIO 20) clicked!")

        if prev_btn3 == GPIO.HIGH and btn3 == GPIO.LOW:
            print("Button 3 (GPIO 21) clicked!")

        # Update previous states
        prev_btn1 = btn1
        prev_btn2 = btn2
        prev_btn3 = btn3

        time.sleep(0.01)  # Poll every 10ms

except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()
