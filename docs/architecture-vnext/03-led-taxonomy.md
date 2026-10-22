# LED Taxonomy v1 (Current)

## Goal

Ustandaryzować model światła bez mieszania geometrii, protokołów i sterowania elektrycznego.

## Axes

### 1) Light domain (co świeci)
- `LightComponent`: podstawowa klasa elementu świetlnego (single LED, RGB, RGBW, addressable pixel)
- `LightFixture`: całość/oprawa/urządzenie świetlne (strip, matrix, ring, custom)

### 2) Hardware control (jak sterujemy fizycznie)
- `HardwareControlInterface`:
  - ADDRESSABLE_DATA
  - ANALOG_PWM
  - CONSTANT_CURRENT_DRIVER

### 3) Communication (jak dane docierają do noda)
- `CommunicationProtocol`: MQTT / SOCKET / WEBAPI / STREAM / UART / EVENT

## White light variants

Dla RGBW i white-only wspieramy profile:
- COLD
- WARM
- NEUTRAL
- TUNABLE

## Classification rule (ważne)

- Pojedyncze diody/LED elementy (także z prostym driverem) to **LightComponent**.
- Dopiero oprawa/całość składająca się z wielu elementów to **LightFixture**.

## Examples

- pojedyncza dioda WS2812 pixel:
  - class = LightComponent
  - HardwareControlInterface = ADDRESSABLE_DATA

- WS2812 strip:
  - class = LightFixture
  - composed_of = LightComponent(ADDRESSABLE_PIXEL)
  - HardwareControlInterface = ADDRESSABLE_DATA

- RGBW analog strip (MOSFET):
  - class = LightFixture
  - composed_of = LightComponent(RGBW)
  - HardwareControlInterface = ANALOG_PWM

- COB white strip:
  - class = LightFixture
  - composed_of = LightComponent(SINGLE_COLOR)
  - HardwareControlInterface = ANALOG_PWM or CONSTANT_CURRENT_DRIVER
