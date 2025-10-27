#!/usr/bin/env python3
import RPi.GPIO as GPIO

def cleanup_all_gpio():
    print("Cleaning up all GPIO pins...")
    GPIO.setwarnings(False)
    GPIO.cleanup()
    print("✅ All GPIO pins released. Safe to disconnect hardware.")

if __name__ == "__main__":
    cleanup_all_gpio()