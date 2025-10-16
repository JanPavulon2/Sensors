# MOSFET Breadboard Layout Guide

## Components Required

- **1x N-Channel MOSFET** (logic-level, e.g., IRLZ44N, 2N7000)
- **1x 220Ω resistor** (Gate protection - GPIO to Gate)
- **1x 10kΩ resistor** (Pull-down - Gate to GND)
- **1x 220Ω-1kΩ resistor** (LED current limiting)
- **1x LED** (any color)
- **Jumper wires**
- **Half-size breadboard** (minimum 30 rows x 10 columns)

## MOSFET Pinout (TO-220 package, flat side facing you)

```
   ┌───────┐
   │       │  ← Metal tab (heatsink)
   │ MOSFET│
   └───┬───┘
       │
   ┌───┴────────────┐
   │   │      │     │
   G   D      S
 Gate Drain Source
(left)(mid)(right)
```

## Breadboard Layout

**Standard breadboard notation:**
- Columns: a, b, c, d, e | f, g, h, i, j
- Rows: 1-30 (numbers)
- Power rails: + and - on both sides

### Visual Layout

```
Power Rails (left side)      Main Area (columns a-j)           Power Rails (right side)

+ +12V ═══════════════════════════════════════════════════════ +12V +

                             Row  a  b  c  d  e | f  g  h  i  j

                              1   •  •  •  •  • | •  •  •  •  •
                              2   •  •  •  •  • | •  •  •  •  •
                              3   •  •  •  •  • | •  •  •  •  •
                              4   •  •  •  •  • | •  •  •  •  •
                              5   •  •  •  •  • | •  •  •  •  •
- GND ═══════════════════════════════════════════════════════ GND -
```

## Component Placement (Exact Coordinates)

**IMPORTANT:** On breadboard, holes a-e in same row are connected internally, and f-j in same row are connected internally. Use this for connections, NOT jumper wires!

### Step 1: Place MOSFET (rows 10-12)

```
MOSFET pins (flat side facing you, legs down):
- Gate (left):    row 10, column c
- Drain (middle): row 11, column c
- Source (right): row 12, column c
```

### Step 2: Gate Resistor 220Ω (GPIO17 → Gate)

```
Resistor spans 3+ holes, uses internal row connection:
- End 1: row 10, column a  (for GPIO17 wire)
- End 2: row 10, column e  (auto-connected to Gate at c10 via breadboard internal connection)

NO jumper wire needed - row 10 holes a-e are all connected!
```

### Step 3: Pull-down Resistor 10kΩ (Gate → GND)

```
Resistor spans rows, connects to Gate via breadboard row:
- End 1: row 10, column f  (connects to Gate - see jumper below)
- End 2: row 14, column f  (for GND wire)

Jumper wire from Gate to other side:
- From: row 10, column d  (same row as Gate, auto-connected)
- To:   row 10, column f  (connects to pull-down resistor)

GND wire:
- From: row 14, column f
- To:   GND rail (-)
```

### Step 4: Source to GND

```
Wire from Source:
- From: row 12, column d  (same row as Source at c12)
- To:   GND rail (-)
```

### Step 5: LED Current Limiting Resistor (Drain → LED)

```
Resistor 220Ω-1kΩ:
- End 1: row 11, column g  (connects to Drain - see jumper below)
- End 2: row 7, column g   (connects to LED)

Jumper from Drain to resistor:
- From: row 11, column e  (same row as Drain at c11)
- To:   row 11, column g  (crosses breadboard gap to connect resistor)
```

### Step 6: LED Placement

```
LED (note polarity!):
- Anode (+, longer leg):  row 7, column i  (same row as resistor end at g7)
- Cathode (-, shorter):   row 5, column i  (for +12V wire)

Wire from LED cathode to power:
- From: row 5, column i
- To:   +12V rail (+)
```

### Step 7: Power Connections

```
GPIO17 wire:
- From: Raspberry Pi GPIO17
- To:   row 10, column a  (Gate resistor end)

Raspberry Pi GND wire:
- From: Raspberry Pi GND pin
- To:   GND rail (-)

Power supply +12V:
- (+) terminal → +12V rail (+)
- (-) terminal → GND rail (-)  [CRITICAL: Common GND with RPi!]
```

## Complete Breadboard Map

```
         a    b    c    d    e  |  f    g    h    i    j
    ─────────────────────────────────────────────────────
 +  ═════════════════════════════════════════════════════  + (+12V)

 1   •    •    •    •    •  |  •    •    •    •    •
 2   •    •    •    •    •  |  •    •    •    •    •
 3   •    •    •    •    •  |  •    •    •    •    •
 4   •    •    •    •    •  |  •    •    •    •    •
 5   •    •    •    •    •  |  •    •    •    •    •
 6   •    •    •    •    •  |  •    •   LED-  •    •  ─┐ to +12V
 7   •    •    •    •    •  |  •    •    •    •    •   │
 8   •    •    •    •    •  | R2━━━━━━━LED+  •    •   │
 9   •    •    •    •    •  |  •    •    •    •    •   │
10  R1━━━━━━━GATE━━━━━━━━━━|━━━━━━━━━R3━━━━━━━━━━━━━━┤ GPIO17→a
11   •    •   DRAIN━━━━━━━━|━━━R2   •    •    •    •   │
12   •    •   SRC━━━━━━━━━━|━━━━━━━━━━━━━━━━━━━━━━━━━┤ to GND
13   •    •    •    •    •  |  •    •   R3━━━━━━━━━━━┤ to GND
14   •    •    •    •    •  |  •    •    •    •    •   │

 -  ═════════════════════════════════════════════════════  - (GND)

Legend:
━━━  Wire or resistor connection
R1   220Ω Gate resistor (GPIO protection)
R2   220Ω-1kΩ LED current limiting resistor
R3   10kΩ Pull-down resistor
GATE MOSFET Gate pin (row 10, col c)
DRAIN MOSFET Drain pin (row 11, col c)
SRC  MOSFET Source pin (row 12, col c)
LED+ LED Anode (longer leg, positive)
LED- LED Cathode (shorter leg, negative)
```

## Wiring Checklist

- [ ] MOSFET inserted: Gate(c10), Drain(c11), Source(c12)
- [ ] 220Ω resistor (a10 to e10) - Gate protection
- [ ] 10kΩ resistor (h10 to h13) - Pull-down
- [ ] Jumper: e10 to c10 (connect Gate resistor to Gate)
- [ ] Jumper: d10 to h10 (connect Gate to pull-down)
- [ ] Jumper: d12 to GND rail (Source to GND)
- [ ] 220Ω-1kΩ resistor (f11 to f8) - LED current limit
- [ ] Jumper: d11 to f11 (Drain to LED resistor)
- [ ] LED anode at h8, cathode at h6
- [ ] Jumper: f8 to h8 (resistor to LED anode)
- [ ] Jumper: h6 to +12V rail (LED cathode to power)
- [ ] GPIO17 wire to a10
- [ ] Raspberry Pi GND to breadboard GND rail
- [ ] +12V power supply (+) to +12V rail
- [ ] +12V power supply (-) to GND rail (COMMON GND!)

## Testing

1. **Before powering:** Use multimeter to verify:
   - No short between +12V and GND
   - Gate to GND = 10kΩ (pull-down resistor)
   - GPIO to Gate = 220Ω (gate resistor)

2. **Power on +12V first** (before running Python script)
   - LED should be OFF

3. **Run Python script:**
   ```bash
   python3 tutorials/mosfet/examples/basic_onoff.py
   ```

4. **Expected behavior:**
   - LED turns ON for 2 seconds
   - LED turns OFF for 2 seconds
   - Repeats

## Troubleshooting

**LED doesn't turn ON:**
- Check MOSFET orientation (flat side away or towards you?)
- Verify Gate is row 10 col c (left pin)
- Check LED polarity (longer leg = anode = positive)
- Measure voltage at Gate when ON (should be ~3.3V)

**LED always ON:**
- Check pull-down resistor (10kΩ must be Gate to GND)
- Verify Source (right pin) is connected to GND

**LED very dim:**
- Check if +12V is actually connected
- Verify current limiting resistor isn't too large (use 220Ω-470Ω)

**GPIO errors:**
- Make sure common GND (RPi and power supply share GND rail)
- Check GPIO permissions (add user to gpio group)

## Safety Notes

⚠️ **IMPORTANT:**
- **ALWAYS connect common GND** between Raspberry Pi and external power supply
- **NEVER exceed GPIO current** (max 16mA per pin) - that's why we use MOSFET!
- **Check MOSFET rating:** Make sure ID (max drain current) > your load current
- **For motors/relays:** Add flyback diode across load
- **Heatsink:** If MOSFET gets hot, add heatsink to metal tab

---

Happy building! 🔧
