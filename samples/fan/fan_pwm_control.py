#!/usr/bin/env python3
"""
PC Fan PWM Control (12V 4-pin)
Direct PWM signal to fan blue wire (no MOSFET needed)

Wiring:
- Fan Black (GND) -> Common GND (Pi + 12V PSU)
- Fan Yellow (+12V) -> 12V PSU (+)
- Fan Blue (PWM) -> GPIO 12
- Fan Green (TACH) -> GPIO 18 (optional, for RPM)
"""
import RPi.GPIO as GPIO
import time

PWM_PIN = 12
PWM_FREQ = 25000  # 25kHz standard for PC fans

GPIO.setmode(GPIO.BCM)
GPIO.setup(PWM_PIN, GPIO.OUT)

fan_pwm = GPIO.PWM(PWM_PIN, PWM_FREQ)
fan_pwm.start(0)

print("PC Fan PWM Control")
print(f"GPIO {PWM_PIN} @ {PWM_FREQ}Hz")
print()

try:
    # Test different speeds
    speeds = [0, 30, 50, 75, 100]

    for speed in speeds:
        print(f"Fan speed: {speed}%")
        fan_pwm.ChangeDutyCycle(speed)
        time.sleep(3)

    # Manual control
    print("\nManual control mode")
    print("Enter speed (0-100) or 'q' to quit")

    while True:
        cmd = input("\nSpeed: ")

        if cmd.lower() == 'q':
            break

        try:
            speed = int(cmd)
            if 0 <= speed <= 100:
                fan_pwm.ChangeDutyCycle(speed)
                print(f"Set to {speed}%")
            else:
                print("Enter 0-100")
        except ValueError:
            print("Invalid input")

except KeyboardInterrupt:
    print("\nStopped")
finally:
    fan_pwm.ChangeDutyCycle(0)
    fan_pwm.stop()
    GPIO.cleanup()
    print("Fan stopped")
