# MOSFET Tutorial for Raspberry Pi 5

## What is a MOSFET?

**MOSFET** (Metal-Oxide-Semiconductor Field-Effect Transistor) is a transistor used as an **electronic switch** or amplifier. In IoT/Raspberry Pi projects, we use it to control high currents (LEDs, motors, relays) with a small GPIO signal.

### MOSFET Pins (TO-220 package, facing flat side):
```
   Left    Middle   Right
    |        |        |
    G        D        S
  (Gate)  (Drain)  (Source)

  GPIO     Load      GND
```

**NOTE**: Pin order can vary by manufacturer! Always check your MOSFET datasheet.
Common packages:
- TO-220: Usually G-D-S (left to right, flat side facing you)
- TO-92: Check datasheet (varies by model)

### MOSFET Types:
- **N-Channel** (N-MOSFET) - turns ON when Gate > Source (most commonly used)
- **P-Channel** (P-MOSFET) - turns ON when Gate < Source

## Wiring Diagram N-MOSFET (LED)

```
                    +12V (or other voltage for LED)
                     |
                     |
                    [R] Resistor (e.g. 220Ω-1kΩ)
                     |
                     |
                    [LED]
                     |
                     |
Raspberry Pi         D (Drain)
                     |
  GPIO17 --------->  G (Gate) [MOSFET]
                     |
  GND ------------>  S (Source)
                     |
                    GND
```

### Important Rules:
1. **Source always to GND** (for N-MOSFET)
2. **Gate connected to GPIO** (3.3V control signal)
3. **Drain connected to load** (LED, motor, etc.)
4. **Common GND** - Raspberry Pi and load power supply must share GND!

### Choosing a MOSFET:
- **Logic-level MOSFET** - turns ON at 3.3V-5V (e.g. IRLZ44N, 2N7000, BS170)
- Check **VGS(th)** (Voltage Gate-Source threshold) - should be < 3V
- Check **ID** (Drain Current) - can it handle your load current?

## Code Examples

This tutorial includes the following examples in the `examples/` directory:

1. **basic_onoff.py** - Simple LED ON/OFF control
2. **pwm_dimming.py** - LED dimming with PWM
3. **motor_control.py** - DC motor speed control
4. **mosfet_controller.py** - Reusable MOSFET controller class

## Running Examples

Make sure you have GPIO permissions:
```bash
sudo usermod -a -G gpio $USER
# Then logout and login again
```

Run any example:
```bash
python3 examples/basic_onoff.py
```

## Troubleshooting

### LED doesn't light up at all:
- ✅ Check connections (loose cables!)
- ✅ Measure voltage on Gate (should be 3.3V when HIGH)
- ✅ Check if Source is connected to GND
- ✅ Check LED polarity (longer leg = anode = +)
- ✅ Check if MOSFET is logic-level (VGS < 3.3V)

### LED is very dim:
- ✅ MOSFET might not be fully ON (use logic-level MOSFET)
- ✅ Resistor too large
- ✅ LED supply voltage too low

### GPIO "already in use" errors:
```bash
sudo python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.cleanup()"
```

### No GPIO permissions:
```bash
sudo usermod -a -G gpio $USER
# Then logout and login
```

## MOSFET Applications:

1. **LED strips control** (12V/24V)
2. **DC motors** (with flyback diode!)
3. **Fans** (12V PC fans)
4. **Solenoid valves** (with flyback diode!)
5. **Relays** (if they need more than 3.3V/40mA)
6. **Heaters** (low voltage)

## Safety:

⚠️ **IMPORTANT**:
- Never exceed maximum Drain current (ID)
- For inductive loads (motors, relays) **ALWAYS** use a flyback diode
- Make sure you have common GND between Raspberry Pi and load power supply
- MOSFET can heat up at high currents - use a heatsink
- Don't connect 230V AC without proper isolation and knowledge!

---

**Happy coding!** 🚀
