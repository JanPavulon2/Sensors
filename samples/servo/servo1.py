import RPi.GPIO as GPIO
import time

# --- KONFIGURACJA ---
SERVO_PIN = 12  # możesz zmienić, np. na 12, 13, 19 itp.

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# --- PWM 50 Hz ---
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(7.5)

def set_speed(speed: float):
    # Przelicz prędkość na wypełnienie PWM (duty cycle)
    # 7.5% = stop, 5% = lewo, 10% = prawo
    duty = 7.5 + (speed * 2.5)
    pwm.ChangeDutyCycle(duty)
    print(f"Speed={speed:+.2f} Duty={duty:.2f}%")

try:
    while True:
        print("Pelna w prawoo")
        set_speed(-1.0)
        time.sleep(2)

        print("STOP")
        set_speed(0.0)
        time.sleep(1)

        print("Pelna w lewo")
        set_speed(-1.0)
        time.sleep(2)

        print("STOP")
        set_speed(0.0)
        time.sleep(2)

except KeyboardInterrupt:
    pass
finally:
    pwm.stop()
    GPIO.cleanup()