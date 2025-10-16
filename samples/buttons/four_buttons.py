#!/usr/bin/env python3
"""
4 Button control with callbacks
GPIO 16, 20, 21, 26
"""
import RPi.GPIO as GPIO
import time

BUTTON_1 = 16
BUTTON_2 = 20
BUTTON_3 = 21
BUTTON_4 = 26  # Fourth button

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)  # Ignore warnings
GPIO.cleanup()  # Clean up any previous GPIO usage
GPIO.setup(BUTTON_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Callback functions
def button1_pressed(channel):
    print("Button 4 (GPIO 16) pressed!")

def button2_pressed(channel):
    print("Button 2 (GPIO 20) pressed!")

def button3_pressed(channel):
    print("Button 3 (GPIO 21) pressed!")

def button4_pressed(channel):
    print("Button 4 (GPIO 26) pressed!")

# Add event detection (FALLING = button pressed)
GPIO.add_event_detect(BUTTON_1, GPIO.FALLING, callback=button1_pressed, bouncetime=200)
GPIO.add_event_detect(BUTTON_2, GPIO.FALLING, callback=button2_pressed, bouncetime=200)
GPIO.add_event_detect(BUTTON_3, GPIO.FALLING, callback=button3_pressed, bouncetime=200)
GPIO.add_event_detect(BUTTON_4, GPIO.FALLING, callback=button4_pressed, bouncetime=200)

print("4 Button callbacks active!")
print("Buttons: GPIO 16, 20, 21, 26")
print("Press Ctrl+C to exit")

try:
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()
