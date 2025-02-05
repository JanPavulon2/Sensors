import time
import pigpio
import dht

GPIO_PIN = 24  # Change to the actual pin

pi = pigpio.pi()
sensor = dht.DHT22(pi, GPIO_PIN)

while True:
    sensor.trigger()
    time.sleep(0.5)
    print(f"AM2301 - Temp: {sensor.temperature():.1f}°C | Humidity: {sensor.humidity():.1f}%")
    time.sleep(2)
