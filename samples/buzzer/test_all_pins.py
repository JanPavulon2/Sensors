#!/usr/bin/env python3
"""
Test which GPIO pins are actually working
"""
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Test these pins
TEST_PINS = [12, 13, 18, 19, 21, 22, 23, 24, 25, 26, 27]

print("Testing GPIO pins for basic output...")
print("=" * 60)

for pin in TEST_PINS:
    try:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

        # Try to set HIGH
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(pin, GPIO.LOW)

        print(f"✓ GPIO {pin:2d} - WORKS (pin responds)")

    except Exception as e:
        print(f"✗ GPIO {pin:2d} - FAILED ({str(e)[:40]})")
    finally:
        try:
            GPIO.setup(pin, GPIO.IN)
        except:
            pass

GPIO.cleanup()
print("=" * 60)
print("\nWhich pins showed ✓ (WORKS)?")
