# Hardware Setup

## LED Strips

**Type:** WS2811 (12V addressable LED strips)
- NOT WS2812B (5V)
- 12V voltage requirement
- Each WS2811 IC controls 3 physical LEDs (RGB triplet)

## Power Supply

**Model:** Mean Well LRS-150-12
- **Output:** 12V DC, 12.5A (150W)
- Professional-grade switching power supply
- Specifically designed for LED applications
- High quality, stable output with minimal noise

## Raspberry Pi GPIO Connections

### Preview LEDs
- GPIO: 18
- Count: 8 pixels
- Color order: GRB
- Max brightness: 100

### Main Strip
- GPIO: 19
- Count: 45 pixels (15 WS2811 ICs × 3 LEDs each)
- Color order: BRG
- Max brightness: 255

### Encoders
- Zone selector: CLK=5, DT=6, SW=13
- Modulator: CLK=16, DT=20, SW=21

### Buttons
- GPIOs: 22, 26, 23, 24

## Notes

- WS2811 operates at 12V, requires appropriate level shifting from Raspberry Pi 3.3V GPIO
- Each pixel in software represents 3 physical LEDs on the strip
- High-quality power supply ensures stable operation even during animations and high current draw
