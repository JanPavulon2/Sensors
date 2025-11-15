import RPi.GPIO as GPIO
import time

servo_pin = 12  # lub inny z PWM, np. 12, 13, 19
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)

pwm = GPIO.PWM(servo_pin, 50)  # 50 Hz
pwm.start(0)

def set_angle(angle):
    duty = 2 + (angle / 18)  # przeliczenie kąta (0–180) na duty cycle (2–12%)
    GPIO.output(servo_pin, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    GPIO.output(servo_pin, False)
    pwm.ChangeDutyCycle(0)

try:
    while True:
        set_angle(0)
        time.sleep(1)
        set_angle(90)
        time.sleep(1)
        set_angle(180)
        time.sleep(1)

except KeyboardInterrupt:
    pwm.stop()
    GPIO.cleanup()
