import time
import board
import adafruit_dht
import signal
import sys
import smbus2
import requests
import json

### CONFIGURATION ###
API_URL = "http://your-server-ip:5000/api/sensors"  # Replace with your C# API URL
DHT_READ_INTERVAL = 2  # Read sensors every 2 seconds
LOG_INTERVAL = 10  # Send data every 10 seconds
MOVING_AVERAGE_SIZE = 5  # Number of readings to average

# I2C address for AM2320
AM2320_I2C_ADDR = 0x5C

### CALIBRATION OFFSETS ###
DHT1_TEMP_OFFSET = 0.0
DHT1_HUM_OFFSET = 2.0

DHT2_TEMP_OFFSET = 0.0
DHT2_HUM_OFFSET = -5.0

AM2320_TEMP_OFFSET = 0.0
AM2320_HUM_OFFSET = -1.0

### INITIALIZE SENSORS ###
SENSOR_DHT1 = adafruit_dht.DHT22(board.D18)
SENSOR_DHT2 = adafruit_dht.DHT22(board.D23)
i2c = smbus2.SMBus(1)

# Store readings for averaging
dht1_temp_readings, dht1_hum_readings = [], []
dht2_temp_readings, dht2_hum_readings = [], []
am2320_temp_readings, am2320_hum_readings = []

last_log_time = time.time()

### SENSOR FUNCTIONS ###

def read_am2320():
    """Reads temperature and humidity from AM2320 via I2C, with error handling."""
    try:
        try:
            i2c.write_i2c_block_data(AM2320_I2C_ADDR, 0x00, [])
        except OSError:
            pass  
        i2c.write_i2c_block_data(AM2320_I2C_ADDR, 0x03, [0x00, 0x04])
        time.sleep(0.002)  
        data = i2c.read_i2c_block_data(AM2320_I2C_ADDR, 0x00, 8)

        humidity = ((data[2] << 8) | data[3]) / 10.0
        temperature = ((data[4] << 8) | data[5]) / 10.0
        return temperature, humidity

    except OSError as e:
        print(f"[AM2320] I2C Error: {e}. Resetting I2C bus...")
        reset_i2c()
        return None, None


def reset_i2c():
    """Resets the I2C bus to clear any stuck communication."""
    global i2c
    try:
        i2c.close()
        time.sleep(1)
        i2c = smbus2.SMBus(1)
        print("[I2C] Bus reset successful.")
    except Exception as e:
        print(f"[I2C] Failed to reset: {e}")


def read_dht(sensor, name):
    """Reads temperature and humidity from a DHT22 sensor."""
    try:
        temp = sensor.temperature
        hum = sensor.humidity
        return temp, hum
    except RuntimeError as e:
        print(f"[{name}] Error: {e}")
        return None, None


def add_to_moving_average(readings_list, value):
    """Adds a new value to the moving average list, keeping only the last N readings."""
    if value is not None:
        readings_list.append(value)
        if len(readings_list) > MOVING_AVERAGE_SIZE:
            readings_list.pop(0)


def calculate_average(readings_list):
    """Calculates the moving average, ignoring None values."""
    valid_readings = [r for r in readings_list if r is not None]
    return sum(valid_readings) / len(valid_readings) if valid_readings else None


def send_data_to_api(data):
    """Sends sensor data as JSON to the C# Web API."""
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(API_URL, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            print("[API] Data sent successfully!")
        else:
            print(f"[API] Failed to send data. Status Code: {response.status_code}")
    except Exception as e:
        print(f"[API] Error sending data: {e}")


### CLEANUP HANDLING ###
def cleanup_and_exit(signal_received, frame):
    """Handles script exit, ensuring GPIOs are released properly."""
    print("\nScript stopped. Cleaning up sensors...")
    SENSOR_DHT1.exit()
    SENSOR_DHT2.exit()
    i2c.close()
    time.sleep(1)
    print("Cleanup complete. Exiting.")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTSTP, cleanup_and_exit)

### MAIN LOOP ###
print("Starting sensor readings... Press Ctrl+C to exit.")

while True:
    try:
        # Read DHT sensors
        dht1_temp, dht1_hum = read_dht(SENSOR_DHT1, "DHT1")
        dht2_temp, dht2_hum = read_dht(SENSOR_DHT2, "DHT2")

        # Read AM2320 sensor
        am2320_temp, am2320_hum = read_am2320()

        # Store readings in moving average lists
        add_to_moving_average(dht1_temp_readings, dht1_temp)
        add_to_moving_average(dht1_hum_readings, dht1_hum)
        add_to_moving_average(dht2_temp_readings, dht2_temp)
        add_to_moving_average(dht2_hum_readings, dht2_hum)
        add_to_moving_average(am2320_temp_readings, am2320_temp)
        add_to_moving_average(am2320_hum_readings, am2320_hum)

        # Check if it's time to send data
        if time.time() - last_log_time >= LOG_INTERVAL:
            last_log_time = time.time()

            data = {
                "DHT1": {"temperature": calculate_average(dht1_temp_readings) + DHT1_TEMP_OFFSET,
                         "humidity": calculate_average(dht1_hum_readings) + DHT1_HUM_OFFSET},
                "DHT2": {"temperature": calculate_average(dht2_temp_readings) + DHT2_TEMP_OFFSET,
                         "humidity": calculate_average(dht2_hum_readings) + DHT2_HUM_OFFSET},
                "AM2320": {"temperature": calculate_average(am2320_temp_readings) + AM2320_TEMP_OFFSET,
                           "humidity": calculate_average(am2320_hum_readings) + AM2320_HUM_OFFSET}
            }

            send_data_to_api(data)

        time.sleep(DHT_READ_INTERVAL)

    except Exception as e:
        print(f"Unexpected error: {e}")
        time.sleep(2)
