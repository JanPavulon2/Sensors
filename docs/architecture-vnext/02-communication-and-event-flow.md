# Communication & Event Flow v1 (Current)

## Communication channels

### Host <-> Frontend
- WebAPI (REST)
- WebSocket/Socket stream (state/live updates)

### Host <-> Nodes (RPi/ESP32/Frontend-runtime)
- MQTT
- Socket / stream
- WebAPI
- UART (tam gdzie ma sens)

### Node <-> Hardware
- GPIO
- PWM / MOSFET
- Addressable data line (WS281x-like)
- I2C / SPI / UART drivers

## Event-first model (default)

Model preferowany na teraz (event-driven reaction):

1. **Event** sygnalizuje, że coś się stało (hardware/UI/integracja/system)
2. Host przechwytuje event i uruchamia logikę reguł/aplikacji
3. Host emituje **Command** jako reakcję (co ma się stać dalej)
4. Wykonanie command może zmienić stan
5. Zmiana stanu publikuje event stanu do subskrybentów

Czyli:
- event = fakt wejściowy / trigger
- command = intencja reakcji systemu

## Frontend refresh exception / projection event

Wyjątek praktyczny (UI):
- po zmianie stanu emitowany jest event projekcyjny, np. `state:changed`
- frontend subskrybuje ten event i odświeża widok

To nie zmienia modelu event-first; to tylko publiczny event projekcyjny pod UI.

## Event naming convention

Format (ogół -> szczegół):

`domain:entity:action[:detail]`

Przykłady:
- `state:zone:changed`
- `hardware:button:pressed`
- `hardware:encoder:rotated`
- `system:node:connected`
- `ui:session:connected`

## Voice input

Voice działa jako kolejne źródło eventów wejściowych:

`voice_input -> transcript_event -> parsed_intent_event -> reaction_command -> state_change -> state_event`

Przykładowe eventy voice:
- `voice:input:started`
- `voice:input:stopped`
- `voice:transcript:received`
- `voice:intent:parsed`
- `voice:command:executed`
- `voice:command:rejected`
