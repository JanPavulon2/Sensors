# WS2811/WS2812B LED Strip Setup Guide

## Hardware Requirements

- **WS2811 or WS2812B ARGB LED strip** (5V)
- **5V power supply** (calculate: ~60mA per LED at full white)
  - 30 LEDs = ~1.8A minimum
  - 60 LEDs = ~3.6A minimum
- **Raspberry Pi** with GPIO 18 (PWM capable pin)

## Wiring

```
LED Strip          Raspberry Pi       5V Power Supply
─────────          ────────────       ───────────────

DIN (Data) ─────→  GPIO 18 (PWM0)
+5V ───────────────────────────────→ (+) 5V
GND ───────────→   GND      ←────────  (-) GND
```

**CRITICAL:**
- **Common GND** - Pi and power supply MUST share GND
- **GPIO 18** is required (PWM hardware pin)
- **Don't power >10 LEDs from Pi 5V** - use external power supply!

### GPIO Pin Options (PWM capable)

Only these GPIO pins work with WS281x:
- **GPIO 10** (PWM0) - conflicts with SPI
- **GPIO 12** (PWM0)
- **GPIO 18** (PWM0) - **RECOMMENDED**
- **GPIO 21** (PWM1)

## Software Installation

### Step 1: Install Python library

```bash
# Activate your virtual environment first
source diunaenv/bin/activate

# Install rpi-ws281x library
pip install rpi-ws281x
```

### Step 2: Run with sudo (required for PWM access)

```bash
sudo /home/jp2/Projects/diuna/diunaenv/bin/python3 tutorials/led_strip/rainbow_animation.py
```

**OR** add user to gpio group (one-time setup):

```bash
sudo usermod -a -G gpio $USER
# Logout and login again
```

Then you can run without sudo:
```bash
python3 tutorials/led_strip/rainbow_animation.py
```

## Configuration

Edit LED_COUNT in the Python files to match your strip:

```python
LED_COUNT = 30          # Change to your LED count
LED_PIN = 18            # GPIO pin
LED_BRIGHTNESS = 255    # 0-255 (lower to save power)
```

## Examples

### 1. Rainbow Animation
```bash
python3 tutorials/led_strip/rainbow_animation.py
```

Animations:
- Rainbow cycle
- Color wipe (red, green, blue)
- Theater chase

### 2. Simple Colors
```bash
python3 tutorials/led_strip/simple_colors.py
```

Interactive RGB control

## Troubleshooting

**No lights:**
- Check GPIO 18 connection to DIN
- Verify 5V power supply is ON and connected
- Check common GND between Pi and power supply
- Run with sudo or check gpio group membership

**Wrong colors:**
- Some strips are GRB instead of RGB
- Change Color() order: `Color(g, r, b)` instead of `Color(r, g, b)`

**Flickering:**
- Power supply too weak (check amperage)
- Loose connection on DIN wire
- Add 470Ω resistor between GPIO 18 and DIN (optional, reduces signal reflection)

**Library error:**
```
ImportError: No module named rpi_ws281x
```
Install library: `pip install rpi-ws281x`

**Permission denied:**
```
RuntimeError: ws2811_init failed
```
Run with sudo or add user to gpio group

## Power Calculation

Each LED draws approximately:
- **~20mA** at dim colors
- **~60mA** at full white (255, 255, 255)

**Example:**
- 30 LEDs × 60mA = 1800mA = **1.8A minimum**
- Recommended: **2-3A power supply** (safety margin)

## Safety Notes

⚠️ **IMPORTANT:**
- **Never power many LEDs from Pi 5V pin** (max 2A total for whole Pi)
- **Always use external 5V power supply** for >10 LEDs
- **Common GND is critical** - Pi and PSU must share GND
- **Check power supply rating** - underpowered = dim/flickering LEDs
- **Lower brightness to save power** - 50% brightness = ~25% power usage

---

Happy lighting! ✨
