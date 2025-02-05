import RPi.GPIO as GPIO
import time

LED_PIN = 17  # GPIO17 (Physical Pin 11)

GPIO.setmode(GPIO.BCM)  # Use GPIO numbers
GPIO.setup(LED_PIN, GPIO.OUT)  # Set as output

try:
    while True:
        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn LED ON
        time.sleep(1)  # Wait 1 second
        GPIO.output(LED_PIN, GPIO.LOW)   # Turn LED OFF
        time.sleep(1)  # Wait 1 second
except KeyboardInterrupt:
    GPIO.cleanup()  # Reset GPIO settings
