"""
PC Fan control using pigpio hardware PWM (active-low MOSFET)
- Uses BCM pin 12 (hardware PWM)
- Frequency 25 kHz
- Inverted logic: user 0% => fan full, 100% => fan off
- Ensures fan is OFF when script exits
"""

import pigpio
import time
import sys

FAN_GPIO = 12         # BCM
PWM_FREQ = 25000      # 25 kHz
MAX_DUTY = 1_000_000  # pigpio uses 0..1_000_000

pi = pigpio.pi()
if not pi.connected:
    print("Cannot connect to pigpiod. Start it: sudo systemctl start pigpiod")
    sys.exit(1)

def set_speed(percent):
    """User percent 0..100 -> inverted duty for active-low fan"""
    percent = max(0, min(100, int(percent)))
    inverted = 100 - percent
    duty = int(inverted * 10_000)  # because 100% -> 1_000_000
    pi.hardware_PWM(FAN_GPIO, PWM_FREQ, duty)

try:
    print("Starting: fan OFF by default (100% inverted)")
    # Ensure fan OFF at start
    set_speed(100)
    time.sleep(0.1)

    # quick sweep test
    for s in (0, 25, 50, 75, 100):
        print(f"Test set {s}% (user scale)")
        set_speed(s)
        time.sleep(2)

    print("Manual mode: enter 0..100 or q to quit")
    while True:
        v = input("speed%: ").strip()
        if v.lower() == 'q':
            break
        try:
            s = int(v)
            set_speed(s)
            print(f"Set {s}%")
        except Exception as e:
            print("bad input", e)

except KeyboardInterrupt:
    print("\nInterrupted")

finally:
    print("Setting fan OFF and cleaning up")
    set_speed(100)     # user=100% => inverted 0% duty = line HIGH => fan OFF
    time.sleep(0.05)
    pi.hardware_PWM(FAN_GPIO, 0, 0)   # stop PWM on that pin
    pi.stop()
    print("Done")