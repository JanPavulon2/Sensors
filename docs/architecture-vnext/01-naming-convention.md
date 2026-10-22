# Naming Convention v3 (Proposed)

## Brainstorm — candidate names for lowest hardware level

| Candidate | Intuicyjność | Plusy | Minusy | Verdict |
|---|---|---|---|---|
| Component | średnia | popularne w software | myli się z UI/software components | odradzane |
| Device | niska (dla elementów prostych) | znane słowo | za szerokie dla button/led/mosfet | odradzane |
| Peripheral | wysoka | sprzętowo precyzyjne, krótkie | mniej popularne w UI nomenklaturze | **rekomendowane** |
| Element | średnia | neutralne | za ogólne | opcjonalne |
| Endpoint | niska | dobrze brzmi przy sieci | myli warstwy runtime/network | odradzane |

## Brainstorm — candidate names for middle aggregate level

| Candidate | Intuicyjność | Plusy | Minusy | Verdict |
|---|---|---|---|---|
| Module | wysoka | zgodne z językiem potocznym i hardware | w software bywa mylące, ale kontekst tu jest jasny | **rekomendowane** |
| Fixture | średnia | dobre dla światła | gorsze poza domeną LED | domenowe |
| Assembly | średnia | inżyniersko poprawne | mniej naturalne w codziennym użyciu | opcjonalne |
| CompositeDevice | średnia | opisowe | długie i ciężkie | odradzane |

## Final proposal (current)

- **Host**: centralny orchestrator (rola logiczna)
- **Node**: typ wykonawczego endpointu (zamiast `NodeDefinition`)
- **NodeInstance**: realny egzemplarz Node
- **Module**: złożony blok hardware z kilku peripheral
- **Peripheral**: najniższy element hardware (Button/Relay/WhiteLed/Encoder/MosfetChannel)
- **Port** / **Connection**: bez zmian
- **CommunicationProtocol** / **HardwareControlInterface**: bez zmian

## Co trafia do core, a co poza core

### Core (stabilne kontrakty domenowe)
- `HostEngine` (orchestracja)
- `Node`
- `NodeInstance`
- `Module` (model docelowy)
- `Peripheral`
- `Port`, `Connection`
- `SignalType`, `PortDirection`
- `CommunicationProtocol`, `HardwareControlInterface`

### Poza core (feature/application/adapters)
- konkretne integracje MQTT/WebAPI/Socket/UART
- konkretne drivery GPIO/PWM/WS281x/I2C/SPI
- use-case workflows (automation rules, policy execution)
- frontend projection models i UI stores

## Class naming style for peripherals

- `WhiteLed`
- `RgbLed`
- `ArgbLed`
- `Relay`
- `Button`
- `Encoder`
- `MosfetChannel`
