import time
import board
import adafruit_dht

# Define the sensor using GPIO24 (change if using another pin)
SENSOR_AM2301 = adafruit_dht.DHT22(board.D24)  # AM2301 behaves like DHT22

while True:
    try:
        temperature = SENSOR_AM2301.temperature
        humidity = SENSOR_AM2301.humidity
        print(f"AM2301 - Temp: {temperature:.1f}°C | Humidity: {humidity:.1f}%")
    except RuntimeError as e:
        print(f"[AM2301] Error: {e}")
    time.sleep(2)
