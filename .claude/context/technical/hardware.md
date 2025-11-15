---
Last Updated: 2025-11-15
Created By: Migration from HARDWARE.md
Purpose: Hardware specifications and GPIO mappings
---

# Hardware Specifications

## LED Strips

**Main Strip**
- Type: WS2811 (12V addressable, NOT WS2812B)
- GPIO: 18 (PWM0)
- Pixels: 90 addressable (= 30 ICs × 3 LEDs each)
- Color Order: BRG
- Zones: 8 logical zones (see zones.md)

**Preview Panel**
- Type: WS2812B (5V, CJMCU-2812-8 module)
- GPIO: 19 (PCM/PWM1)
- Pixels: 8
- Color Order: GRB
- Orientation: Upside down (requires index reversal)

## Power Supply

**Model**: Mean Well LRS-150-12
- Output: 12V DC, 12.5A (150W)
- Professional switching supply
- Stable output, minimal noise

**Power Budget**:
- Full white: 5.4A peak (90px × 60mA)
- Typical: 2-3A (mixed colors)
- Per-zone injection prevents voltage drop

## GPIO Mapping

**Encoders**:
- Selector: CLK=5, DT=6, SW=13
- Modulator: CLK=16, DT=20, SW=21

**Buttons**:
- BTN1 (22): Toggle edit mode
- BTN2 (26): Lamp white mode
- BTN3 (23): Power toggle
- BTN4 (24): STATIC ↔ ANIMATION mode switch

**LED Strips**:
- Main: GPIO 18 (WS2811)
- Preview: GPIO 19 (WS2812B)

## Critical Constraints

**WS281x GPIO Restriction**:
Only pins 10, 12, 18, 21 work (PWM/PCM peripherals required)
- GPIO 19 works in testing but not officially supported

**DMA Channel**:
Single DMA channel = only one `strip.show()` at a time

**Timing Requirements**:
- Data rate: 800kHz
- DMA transfer: 2.7ms for 90 pixels
- Reset pulse: 50µs minimum
- Min frame time: 2.75ms total

**Thermal**:
- WS2811 rated: -25°C to +80°C
- Typical operation: 40-50°C with airflow
- Monitor lamp zone (19 pixels continuous)

## Raspberry Pi Model

**Recommended**: Pi 4 (2GB+)
- Target FPS: 60Hz stable
- CPU usage: 20-30%
- Excellent headroom

**Acceptable**: Pi 3B/3B+
- Target FPS: 50-60Hz
- CPU usage: 35-55%
- Minor GC jitter

**Not Recommended**: Pi Zero
- Target FPS: 30-40Hz
- CPU usage: 70-90%
- Single core bottleneck