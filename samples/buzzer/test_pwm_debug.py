#!/usr/bin/env python3
"""
Diagnostic script to test GPIO 12 PWM directly
"""

import sys

# Set UTF-8 encoding for output BEFORE any imports (fixes Unicode symbol rendering)
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
if hasattr(sys.stderr, 'reconfigure') and sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore


import RPi.GPIO as GPIO
import time

BUZZER_PIN = 19

print("=" * 60)
print("GPIO 12 PWM Diagnostic Test")
print("=" * 60)

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)

print(f"✓ GPIO {BUZZER_PIN} configured as OUTPUT")

try:
    # Test 1: Digital ON/OFF (baseline)
    print("\n[Test 1] Digital ON/OFF (5 quick beeps)")
    for i in range(5):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.05)
    print("✓ Digital test complete (you should hear 5 beeps)")

    time.sleep(1)

    # Test 2: PWM at 440 Hz
    print("\n[Test 2] PWM @ 440 Hz, 80% duty cycle, 2 seconds")
    pwm = GPIO.PWM(BUZZER_PIN, 440)
    pwm.start(80)  # 80% duty cycle
    time.sleep(2)
    pwm.stop()
    print("✓ PWM test complete (you should hear a steady tone)")

    time.sleep(1)

    # Test 3: PWM frequency sweep
    print("\n[Test 3] Frequency sweep (440Hz → 2000Hz)")
    pwm = GPIO.PWM(BUZZER_PIN, 440)
    pwm.start(80)
    for freq in [440, 800, 1200, 1600, 2000]:
        print(f"  Playing {freq} Hz...")
        pwm.ChangeFrequency(freq)
        time.sleep(0.5)
    pwm.stop()
    print("✓ Sweep test complete")

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("- Heard 5 beeps in Test 1? → GPIO output works ✓")
    print("- Heard tone in Test 2?     → PWM generation works ✓")
    print("- Heard pitch change?        → Frequency control works ✓")
    print("=" * 60)

except KeyboardInterrupt:
    print("\n⚠ Test interrupted by user")
finally:
    GPIO.cleanup()
    print("✓ GPIO cleanup complete")
