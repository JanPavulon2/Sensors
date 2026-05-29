import lgpio
import time

PWM_PIN = 12
PWM_FREQ = 1000  # Hz

h = lgpio.gpiochip_open(0)

try:
    # TO BYŁO BRAKUJĄCE
    lgpio.gpio_claim_output(h, PWM_PIN)

    print("PWM LED dimming started")

    while True:

        # rozjaśnianie
        for duty in range(0, 101):
            lgpio.tx_pwm(h, PWM_PIN, PWM_FREQ, duty)
            time.sleep(0.01)

        # ściemnianie
        for duty in range(100, -1, -1):
            lgpio.tx_pwm(h, PWM_PIN, PWM_FREQ, duty)
            time.sleep(0.01)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    lgpio.tx_pwm(h, PWM_PIN, 0, 0)
    lgpio.gpiochip_close(h)

    print("Clean exit")