#!/usr/bin/env python3
"""
Simple button reading - GPIO 16, 20, 21
Wiring: One button leg to GND, other leg to GPIO
"""
import RPi.GPIO as GPIO
import time

# Button pins
BUTTON_1 = 16
BUTTON_2 = 20
BUTTON_3 = 21

# Setup
GPIO.setmode(GPIO.BCM)

# Setup buttons with internal pull-up resistors
# When button pressed: GPIO reads LOW (0)
# When button released: GPIO reads HIGH (1)
GPIO.setup(BUTTON_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Button tester started!")
print("Press buttons on GPIO 16, 20, 21")
print("Press Ctrl+C to exit")

try:
    while True:
        # Read button states (LOW = pressed, HIGH = released)
        btn1_state = GPIO.input(BUTTON_1)
        btn2_state = GPIO.input(BUTTON_2)
        btn3_state = GPIO.input(BUTTON_3)

        # Print when button is pressed (state = 0/LOW)
        if btn1_state == GPIO.LOW:
            print("Button 1 (GPIO 16) PRESSED")
            time.sleep(0.2)  # Debounce delay

        if btn2_state == GPIO.LOW:
            print("Button 2 (GPIO 20) PRESSED")
            time.sleep(0.2)

        if btn3_state == GPIO.LOW:
            print("Button 3 (GPIO 21) PRESSED")
            time.sleep(0.2)

        time.sleep(0.01)  # Small delay to prevent CPU overuse

except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()
