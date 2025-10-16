#!/usr/bin/env python3
"""
PC Fan Control with RPM reading
Reads fan speed via TACH signal (green wire)

Wiring:
- Fan control via MOSFET on GPIO 12 (PWM)
- Fan TACH (green) → GPIO 18 (for RPM reading)

Note: TACH signal pulses 2x per revolution (most fans)
"""
import RPi.GPIO as GPIO
import time
from threading import Thread

FAN_PWM_PIN = 12
FAN_TACH_PIN = 18
PWM_FREQ = 25000

# RPM calculation variables
pulse_count = 0
rpm = 0

def tach_pulse(channel):
    """Count TACH pulses"""
    global pulse_count
    pulse_count += 1

def calculate_rpm():
    """Calculate RPM every second"""
    global pulse_count, rpm
    while True:
        time.sleep(1)
        # Most fans: 2 pulses per revolution
        rpm = (pulse_count / 2) * 60
        pulse_count = 0
        print(f"Fan RPM: {int(rpm)}")

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_PWM_PIN, GPIO.OUT)
GPIO.setup(FAN_TACH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Setup PWM
fan_pwm = GPIO.PWM(FAN_PWM_PIN, PWM_FREQ)
fan_pwm.start(0)

# Setup TACH interrupt
GPIO.add_event_detect(FAN_TACH_PIN, GPIO.FALLING, callback=tach_pulse)

# Start RPM monitoring thread
rpm_thread = Thread(target=calculate_rpm, daemon=True)
rpm_thread.start()

print("PC Fan with RPM monitoring")
print("Control via GPIO 12, RPM via GPIO 18")
print()

try:
    # Test speeds
    for speed in [30, 50, 75, 100]:
        print(f"\nSetting speed to {speed}%")
        fan_pwm.ChangeDutyCycle(speed)
        time.sleep(5)

    # Manual control
    print("\nManual control mode")
    while True:
        user_input = input("\nFan speed (0-100, 'q' to quit): ")

        if user_input.lower() == 'q':
            break

        try:
            speed = int(user_input)
            if 0 <= speed <= 100:
                fan_pwm.ChangeDutyCycle(speed)
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
