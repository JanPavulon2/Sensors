#!/usr/bin/env python3
"""
Example 3: DC Motor Control
WARNING: For motors, use a flyback diode parallel to the motor!

Wiring (MOSFET flat side facing you, TO-220 package):

        +12V
         |
      [MOTOR]
         |
       [DIODE] (cathode to +12V, anode to motor-)
         |
         D (Drain - middle pin)
         |
         +--------+--------+
         |        |        |
         G        D        S
       (Gate)  (Drain)  (Source)
         |                 |
      GPIO17              GND
"""
import RPi.GPIO as GPIO
import time

MOTOR_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(MOTOR_PIN, GPIO.OUT)

# PWM for speed control
pwm = GPIO.PWM(MOTOR_PIN, 1000)
pwm.start(0)

try:
    # Gradual acceleration
    print("Accelerating...")
    for speed in range(0, 101, 10):
        print(f"Speed: {speed}%")
        pwm.ChangeDutyCycle(speed)
        time.sleep(0.5)

    # Full speed for 3 seconds
    print("Full speed!")
    time.sleep(3)

    # Stop
    print("Stopping...")
    pwm.ChangeDutyCycle(0)

except KeyboardInterrupt:
    print("\nSTOP")
finally:
    pwm.stop()
    GPIO.cleanup()
