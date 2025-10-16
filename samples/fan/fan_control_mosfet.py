#!/usr/bin/env python3
"""
PC Fan (4-pin PWM) Control via MOSFET
Safe method using MOSFET switching

Wiring:
- Fan Yellow (+12V) → +12V power supply
- Fan Black (GND) → Through MOSFET Drain-Source → GND
- Fan Blue (PWM) → Leave disconnected (or via optocoupler)
- Fan Green (TACH) → Optional GPIO 18 for RPM reading

MOSFET:
- Gate → GPIO 12 (through 220Ω resistor)
- Drain → Fan Black (GND wire)
- Source → GND
- 10kΩ pull-down: Gate to GND
"""
import RPi.GPIO as GPIO
import time

FAN_PIN = 12  # Hardware PWM pin
PWM_FREQ = 25000  # 25kHz for PC fans (standard PWM frequency)

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_PIN, GPIO.OUT)

# Create PWM object
fan_pwm = GPIO.PWM(FAN_PIN, PWM_FREQ)
fan_pwm.start(0)  # Start at 0% (fan off)

print("PC Fan Controller (via MOSFET)")
print("GPIO 12 @ 25kHz PWM")
print()

try:
    # Test different speeds
    speeds = [0, 25, 50, 75, 100]

    for speed in speeds:
        print(f"Setting fan speed to {speed}%")
        fan_pwm.ChangeDutyCycle(speed)
        time.sleep(3)

    print("\nEntering manual control mode")
    print("Commands: 0-100 (speed %), 'q' to quit")

    while True:
        user_input = input("Fan speed (0-100): ")

        if user_input.lower() == 'q':
            break

        try:
            speed = int(user_input)
            if 0 <= speed <= 100:
                fan_pwm.ChangeDutyCycle(speed)
                print(f"Fan speed set to {speed}%")
            else:
                print("Enter value 0-100")
        except ValueError:
            print("Invalid input")

except KeyboardInterrupt:
    print("\nStopped")
finally:
    fan_pwm.ChangeDutyCycle(0)  # Turn off fan
    fan_pwm.stop()
    GPIO.cleanup()
    print("Fan stopped, GPIO cleaned up")
