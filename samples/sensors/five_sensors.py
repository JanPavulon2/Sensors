import time
import board
import adafruit_dht
import signal
import sys
import smbus2

### CONFIGURATION ###
DHT_READ_INTERVAL = 3  # How often to read sensors (seconds)
LOG_INTERVAL = 15  # How often to save/log data (seconds)
MOVING_AVERAGE_SIZE = 7  # Number of readings to average

# I2C addresses & buses for AM2320 sensors
AM2320_I2C_ADDR = 0x5C
I2C_BUS_1 = 1  # First I2C bus
I2C_BUS_2 = 3  # Second I2C bus

### CALIBRATION OFFSETS ###
DHT1_TEMP_OFFSET = 0.0
DHT1_HUM_OFFSET = 0.0
DHT2_TEMP_OFFSET = 0.0
DHT2_HUM_OFFSET = -4.0
AM2320_1_TEMP_OFFSET = 0.0
AM2320_1_HUM_OFFSET = 2.0
AM2320_2_TEMP_OFFSET = 0.0
AM2320_2_HUM_OFFSET = 0.0
AM2301_TEMP_OFFSET = 0.0
AM2301_HUM_OFFSET = 0.0

### INITIALIZE SENSORS ###
SENSOR_DHT1 = adafruit_dht.DHT22(board.D18)
SENSOR_DHT2 = adafruit_dht.DHT22(board.D23)
SENSOR_AM2301 = adafruit_dht.DHT22(board.D24)  # AM2301 works like DHT22

# I2C Sensors
i2c1 = smbus2.SMBus(I2C_BUS_1)  # First AM2320 on I2C-1
i2c2 = smbus2.SMBus(I2C_BUS_2)  # Second AM2320 on I2C-3

# Store readings for averaging
sensor_readings = {
    "dht1_temp": [], "dht1_hum": [],
    "dht2_temp": [], "dht2_hum": [],
    "am2301_temp": [], "am2301_hum": [],
    "am2320_1_temp": [], "am2320_1_hum": [],
    "am2320_2_temp": [], "am2320_2_hum": []
}

# Track last log time
last_log_time = time.time()

### SENSOR FUNCTIONS ###

def read_am2320(i2c_bus, sensor_name):
    """Reads temperature and humidity from an AM2320 sensor on a given I2C bus."""
    try:
        try:
            i2c_bus.write_i2c_block_data(AM2320_I2C_ADDR, 0x00, [])
        except OSError:
            pass  # Ignore expected wake-up error

        i2c_bus.write_i2c_block_data(AM2320_I2C_ADDR, 0x03, [0x00, 0x04])
        time.sleep(0.002)

        data = i2c_bus.read_i2c_block_data(AM2320_I2C_ADDR, 0x00, 8)

        humidity = ((data[2] << 8) | data[3]) / 10.0
        temperature = ((data[4] << 8) | data[5]) / 10.0
        return temperature, humidity

    except OSError as e:
        print(f"[{sensor_name}] I2C Error: {e}. Resetting I2C bus...")
        reset_i2c(i2c_bus)
        return None, None

def read_dht(sensor, name):
    """Reads temperature and humidity from a DHT22 or AM2301 sensor."""
    try:
        temp = sensor.temperature
        hum = sensor.humidity
        return temp, hum
    except RuntimeError as e:
        print(f"[{name}] Error: {e}")
        return None, None

def reset_i2c(bus_number):
    """Resets a specific I2C bus by creating a new SMBus instance."""
    global i2c1, i2c2

    try:
        if bus_number == I2C_BUS_1:
            i2c1.close()
            time.sleep(1)
            i2c1 = smbus2.SMBus(I2C_BUS_1)
            print(f"[I2C] Bus {I2C_BUS_1} reset successful.")
        elif bus_number == I2C_BUS_2:
            i2c2.close()
            time.sleep(1)
            i2c2 = smbus2.SMBus(I2C_BUS_2)
            print(f"[I2C] Bus {I2C_BUS_2} reset successful.")
    except Exception as e:
        print(f"[I2C] Failed to reset bus {bus_number}: {e}")

def add_to_moving_average(sensor_key, value):
    """Adds a new value to the moving average list, keeping only the last N readings."""
    if value is not None:
        sensor_readings[sensor_key].append(value)
        if len(sensor_readings[sensor_key]) > MOVING_AVERAGE_SIZE:
            sensor_readings[sensor_key].pop(0)

def calculate_average(sensor_key):
    """Calculates the moving average, ignoring None values."""
    valid_readings = [r for r in sensor_readings[sensor_key] if r is not None]
    return sum(valid_readings) / len(valid_readings) if valid_readings else None

### CLEANUP HANDLING ###
def cleanup_and_exit(signal_received, frame):
    """Handles script exit, ensuring GPIOs are released properly."""
    print("\nScript stopped. Cleaning up sensors...")
    SENSOR_DHT1.exit()
    SENSOR_DHT2.exit()
    SENSOR_AM2301.exit()
    i2c1.close()
    i2c2.close()
    time.sleep(1)
    print("Cleanup complete. Exiting.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup_and_exit)  # Handle Ctrl+C
signal.signal(signal.SIGTSTP, cleanup_and_exit)  # Handle Ctrl+Z

### MAIN LOOP ###
print("Starting sensor readings... Press Ctrl+C to exit.")

while True:
    try:
        # Read all sensors
        dht1_temp, dht1_hum = read_dht(SENSOR_DHT1, "DHT1")
        dht2_temp, dht2_hum = read_dht(SENSOR_DHT2, "DHT2")
        am2301_temp, am2301_hum = read_dht(SENSOR_AM2301, "AM2301")
        am2320_1_temp, am2320_1_hum = read_am2320(i2c1, "AM2320-1")
        am2320_2_temp, am2320_2_hum = read_am2320(i2c2, "AM2320-2")

        # Store readings in moving averages
        add_to_moving_average("dht1_temp", dht1_temp)
        add_to_moving_average("dht1_hum", dht1_hum)
        add_to_moving_average("dht2_temp", dht2_temp)
        add_to_moving_average("dht2_hum", dht2_hum)
        add_to_moving_average("am2301_temp", am2301_temp)
        add_to_moving_average("am2301_hum", am2301_hum)
        add_to_moving_average("am2320_1_temp", am2320_1_temp)
        add_to_moving_average("am2320_1_hum", am2320_1_hum)
        add_to_moving_average("am2320_2_temp", am2320_2_temp)
        add_to_moving_average("am2320_2_hum", am2320_2_hum)

        # Check if it's time to log
        if time.time() - last_log_time >= LOG_INTERVAL:
            last_log_time = time.time()

            # Print final stable readings with offsets applied
            print("\n--- SENSOR LOG ---")
            print(f"DHT1 (GPIO18): Temp {calculate_average('dht1_temp') + DHT1_TEMP_OFFSET:.1f}°C, Hum {calculate_average('dht1_hum') + DHT1_HUM_OFFSET:.1f}%")
            print(f"DHT2 (GPIO23): Temp {calculate_average('dht2_temp') + DHT2_TEMP_OFFSET:.1f}°C, Hum {calculate_average('dht2_hum') + DHT2_HUM_OFFSET:.1f}%")
            print(f"AM2301 (GPIO24): Temp {calculate_average('am2301_temp') + AM2301_TEMP_OFFSET:.1f}°C, Hum {calculate_average('am2301_hum') + AM2301_HUM_OFFSET:.1f}%")
            print(f"AM2320-1 (I2C1): Temp {calculate_average('am2320_1_temp') + AM2320_1_TEMP_OFFSET:.1f}°C, Hum {calculate_average('am2320_1_hum') + AM2320_1_HUM_OFFSET:.1f}%")
            print(f"AM2320-2 (I2C3): Temp {calculate_average('am2320_2_temp') + AM2320_2_TEMP_OFFSET:.1f}°C, Hum {calculate_average('am2320_2_hum') + AM2320_2_HUM_OFFSET:.1f}%")
            print("-------------------")

        time.sleep(DHT_READ_INTERVAL)

    except Exception as e:
        print(f"Unexpected error: {e}")
        time.sleep(2)
