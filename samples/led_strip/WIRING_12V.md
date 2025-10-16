# WS2811 12V LED Strip Wiring Guide

## Why 12V Strips Need Level Shifter

**Problem:**
- Raspberry Pi GPIO outputs **3.3V**
- WS2811 12V strips need **5V data signal** (minimum 0.7 × VDD = 3.5V @ 5V logic)
- 3.3V is too low and unreliable!

**Solution:** Use level shifter to convert 3.3V → 5V

## Option 1: 74HCT245 Level Shifter (RECOMMENDED)

### Components:
- 74HCT245 IC (octal bus transceiver)
- 0.1µF capacitor (decoupling)

### Wiring:

```
Raspberry Pi                74HCT245               LED Strip WS2811 12V
────────────                ────────               ────────────────────

3.3V ──────────────────────→ VCC (pin 20)
GPIO 18 ────────────────────→ A1 (pin 2)
                             B1 (pin 18) ─────────→ DIN (Data In)
                             DIR (pin 1) ─────────→ VCC (A→B direction)
                             OE (pin 19) ─────────→ GND (output enable)
GND ────────────────────────→ GND (pin 10)

External 5V (from 12V PSU
with buck converter) ───────→ Connect to 74HCT245 pin 20 (instead of 3.3V)

12V Power Supply:
  (+) ──────────────────────────────────────────→ LED Strip +12V
  (-) ──────────────────────────────────────────→ LED Strip GND

Common GND ←── Pi GND + 74HCT245 GND + 12V PSU GND (ALL CONNECTED!)
```

### 74HCT245 Pinout (DIP-20):

```
       ┌─────────┐
  DIR ─┤1    20├─ VCC (3.3V or 5V)
   A1 ─┤2    19├─ OE (to GND)
   A2 ─┤3    18├─ B1 (to LED DIN)
   A3 ─┤4    17├─ B2
   A4 ─┤5    16├─ B3
   A5 ─┤6    15├─ B4
   A6 ─┤7    14├─ B5
   A7 ─┤8    13├─ B6
   A8 ─┤9    12├─ B7
  GND ─┤10   11├─ B8
       └─────────┘

We only use: A1, B1, DIR, OE, VCC, GND
```

### Minimal Setup:

```
74HCT245 Pin    Connection
────────────    ──────────
1  (DIR)        → VCC (or 3.3V) - sets A→B direction
2  (A1)         → GPIO 18
10 (GND)        → Common GND
18 (B1)         → LED Strip DIN
19 (OE)         → GND (enables output)
20 (VCC)        → 5V (for proper 5V output) OR 3.3V (might work)
```

## Option 2: Simple MOSFET Buffer (Alternative)

If you don't have 74HCT245, use N-channel MOSFET:

```
Raspberry Pi          MOSFET              LED Strip
────────────          ──────              ─────────

GPIO 18 ─[10kΩ]─→ Gate
                   |
5V (external) ─[1kΩ]─┤
                   |
                 Drain ──────────────→ DIN (Data)

GND ───────────→ Source
                   |
                  GND ─────────────→ GND (common)

12V PSU (+) ─────────────────────→ LED +12V
12V PSU (-) ─────────────────────→ Common GND
```

**Note:** This inverts the signal, so you need to configure software for inverted output!

```python
LED_INVERT = True  # Set to True when using MOSFET buffer
```

## Complete Wiring Diagram (74HCT245)

```
                    ┌──────────────┐
                    │  74HCT245    │
                    │              │
GPIO 18 ────────────┤ A1       B1  ├─────→ LED DIN
3.3V ───────────────┤ VCC          │
GND ────────────────┤ GND          │
3.3V ───────────────┤ DIR          │
GND ────────────────┤ OE           │
                    └──────────────┘
                           │
                          GND
                           │
    ┌──────────────────────┴───────────────────┐
    │                                           │
Raspberry Pi GND                          LED Strip GND
    │                                           │
    └───────────────┬───────────────────────────┘
                    │
              12V PSU GND (-)

12V PSU (+12V) ───────────────────────────→ LED Strip +12V
```

## Software Configuration

Same code works! Just wire it up correctly:

```python
# In rainbow_animation.py or simple_colors.py
LED_PIN = 18        # GPIO 18
LED_INVERT = False  # False for 74HCT245, True for MOSFET
```

## Testing Steps

1. **Wire level shifter** (74HCT245 or MOSFET)
2. **Connect 12V power** to LED strip +12V and GND
3. **Verify common GND** - use multimeter between Pi GND and 12V PSU GND (should be 0Ω)
4. **Run test:**
   ```bash
   sudo python3 tutorials/led_strip/simple_colors.py
   ```

## Troubleshooting

**LEDs don't light up:**
- Check 12V power supply
- Verify level shifter has 5V output (measure B1 pin when GPIO high)
- Ensure common GND

**Random colors / flickering:**
- 3.3V signal too weak - use proper 5V level shifter
- Add 0.1µF capacitor near 74HCT245 VCC pin
- Keep DIN wire short (<30cm)

**First few LEDs work, rest don't:**
- Voltage drop in 12V power lines
- Use thicker power wires
- Inject 12V power at multiple points for long strips

## Quick Tip: No Level Shifter?

**Try this HACK (not guaranteed):**
- Connect 470Ω resistor in series: GPIO 18 ──[470Ω]──→ DIN
- Some 12V strips are tolerant to 3.3V
- Works ~50% of the time, depends on strip controller chip

**Better solution:** Order 74HCT245 or use MOSFET buffer!

---

Happy 12V LED strip controlling! ✨
