# from gpiozero import LED
# from time import sleep

# led = LED(21)

# led.on()
# sleep(2)
# led.off()
# sleep(2)

import lgpio
import time

GPIO_PIN = 12  # BCM numbering

# otwarcie chipu GPIO (dla Raspberry Pi zawsze 0)
h = lgpio.gpiochip_open(0)

try:
    # ustaw pin jako wyjście
    lgpio.gpio_claim_output(h, GPIO_PIN)

    while True:
        lgpio.gpio_write(h, GPIO_PIN, 1)  # LED ON
        time.sleep(0.5)

        lgpio.gpio_write(h, GPIO_PIN, 0)  # LED OFF
        time.sleep(0.5)

except KeyboardInterrupt:
    pass

finally:
    # sprzątanie
    lgpio.gpio_write(h, GPIO_PIN, 0)
    lgpio.gpiochip_close(h)