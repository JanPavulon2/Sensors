# Capabilities v1 (Current)

## Cel

Capability opisuje **co dany byt potrafi robić** (funkcjonalność), niezależnie od tego jak jest wdrożony.

To nie jest typ sprzętu ani protokół — to zestaw zdolności.

## Poziomy capability

### 1) Host capabilities
- `orchestrate`
- `state_management`
- `rules_engine`
- `api_exposure`
- `event_distribution`
- `topology_management`

### 2) Node capabilities
- `render_output` (renderowanie światła / output)
- `input_capture` (przyciski/enkodery/sensory/mikrofon)
- `telemetry_publish`
- `command_execution`
- `local_automation`
- `storage_local`

### 3) Device capabilities
- `switch_binary` (on/off)
- `dimming`
- `color_control_rgb`
- `color_control_rgbw`
- `addressable_pixels`
- `sensor_read_temperature`
- `sensor_read_humidity`
- `sound_output`
- `display_output`

### 4) Component capabilities
- `button_press`
- `button_hold`
- `encoder_rotate`
- `relay_channel_switch`
- `single_led_onoff`
- `single_led_pwm`
- `pixel_set_color`

## Capability naming rules

Format:
`domain_action[_detail]`

Przykłady:
- `render_output`
- `input_capture`
- `sensor_read_temperature`
- `color_control_rgbw`
- `relay_channel_switch`

Zasady:
- snake_case
- bez skrótów trudnych do odczytu
- czasownik + obiekt
- bez mieszania poziomów (node capability != component capability)

## Relation do innych pojęć

- **DeviceType / NodeType** = czym to jest
- **Capability** = co to potrafi
- **CommunicationProtocol** = jak się komunikuje
- **HardwareControlInterface** = jak fizycznie steruje hardware

## Przykłady pełne

### ESP32 node do LED strip
- NodeType: `ESP32`
- Node capabilities:
  - `render_output`
  - `command_execution`
  - `telemetry_publish`
- Device (strip fixture) capabilities:
  - `addressable_pixels`
  - `color_control_rgb`

### Panel kontrolny
- NodeType: `RASPBERRY_PI` (lub inny, zależnie od osadzenia)
- Device capabilities:
  - `input_capture`
- Components:
  - button: `button_press`, `button_hold`
  - encoder: `encoder_rotate`

### 8x relay board
- Device capabilities:
  - `switch_binary`
- Component capabilities:
  - `relay_channel_switch`
