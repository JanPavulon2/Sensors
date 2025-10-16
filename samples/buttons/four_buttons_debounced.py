#!/usr/bin/env python3
"""
4 Button control with better debouncing
GPIO 16, 20, 21, 26
"""
import RPi.GPIO as GPIO
import time

BUTTON_1 = 19
BUTTON_2 = 26
BUTTON_3 = 23
BUTTON_4 = 24

DEBOUNCE_TIME = 0.3  # 300ms debounce

# Setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Track last press time for debouncing
last_press = {BUTTON_1: 0, BUTTON_2: 0, BUTTON_3: 0, BUTTON_4: 0}
prev = {BUTTON_1: GPIO.HIGH, BUTTON_2: GPIO.HIGH,
        BUTTON_3: GPIO.HIGH, BUTTON_4: GPIO.HIGH}

print("4 Button control with debouncing")
print("Buttons: GPIO 16, 20, 21, 26")
print("Press Ctrl+C to exit")

try:
    while True:
        current_time = time.time()

        for pin, name in [(BUTTON_1, "Button 1"), (BUTTON_2, "Button 2"),
                          (BUTTON_3, "Button 3"), (BUTTON_4, "Button 4")]:
            state = GPIO.input(pin)

            # Detect falling edge (pressed)
            if prev[pin] == GPIO.HIGH and state == GPIO.LOW:
                # Check if enough time passed since last press
                if (current_time - last_press[pin]) > DEBOUNCE_TIME:
                    print(f"{name} (GPIO {pin}) pressed!")
                    last_press[pin] = current_time

            prev[pin] = state

        time.sleep(0.02)  # 20ms polling

except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()
