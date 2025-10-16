#!/usr/bin/env python3
"""
Button reading with event callbacks (better method)
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

# Callback functions
def button1_pressed(channel):
    print("Button 1 (GPIO 16) pressed!")

def button2_pressed(channel):
    print("Button 2 (GPIO 20) pressed!")

def button3_pressed(channel):
    print("Button 3 (GPIO 21) pressed!")

# Add event detection
# FALLING = transition from HIGH to LOW (button pressed)
# bouncetime = ignore repeated signals within 200ms (debouncing)
GPIO.add_event_detect(BUTTON_1, GPIO.FALLING, callback=button1_pressed, bouncetime=200)
GPIO.add_event_detect(BUTTON_2, GPIO.FALLING, callback=button2_pressed, bouncetime=200)
GPIO.add_event_detect(BUTTON_3, GPIO.FALLING, callback=button3_pressed, bouncetime=200)

print("Button callbacks active!")
print("Press any button (GPIO 16, 20, 21)")
print("Press Ctrl+C to exit")

try:
    # Just wait for events
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()
