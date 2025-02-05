import time
import board
import adafruit_dht
import signal
import sys

# Select the sensor type (DHT11 or DHT22)
SENSOR_1 = adafruit_dht.DHT22(board.D18)  # Change to DHT11 if needed
SENSOR_2 = adafruit_dht.DHT22(board.D23)  # Change to DHT11 if needed

# Function to clean up GPIO on exit
def cleanup_and_exit(signal_received, frame):
    print("\nScript stopped. Cleaning up GPIO...")
    SENSOR_1.exit()  
    SENSOR_2.exit()  
    time.sleep(1)
    print("Cleanup complete. Exiting.")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup_and_exit)  # Handle Ctrl+C
signal.signal(signal.SIGTSTP, cleanup_and_exit)  # Handle Ctrl+Z

try:
    while True:
        try:
            # Read first sensor
            temperature_1 = SENSOR_1.temperature
            humidity_1 = SENSOR_1.humidity
            print(f"Sensor 1 - Temperature: {temperature_1:.1f}°C | Humidity: {humidity_1:.1f}%")

            # Read second sensor
            temperature_2 = SENSOR_2.temperature
            humidity_2 = SENSOR_2.humidity
            print(f"Sensor 2 - Temperature: {temperature_2:.1f}°C | Humidity: {humidity_2:.1f}%")

        except RuntimeError as e:
            print(f"Error reading sensors: {e}")

        time.sleep(2)  # Wait 2 seconds before next reading

except KeyboardInterrupt:
    cleanup_and_exit(None, None)