# Core Multi-Node Model Changes (Summary)

## What changed

- Switched core identity fields in new domain dataclasses from `str` to `UUID`:
  - `Connection`
  - `DeviceDefinition`
  - `DeviceInstance`
  - `NodeInstance`
- Replaced string-backed enums with `Enum + auto()` in:
  - `SignalType`
  - `PortDirection`
  - `NodeType`
- Introduced explicit node modeling with two object-oriented classes:
  - `NodeTemplate` (definition/template)
  - `NodeInstance` (deployed instance)
- Renamed host orchestration entrypoint from `Runtime` to `HostEngine`.
- Added protocol-agnostic node transport contracts:
  - `TransportProtocol`
  - `NodeTransport`
  - `ConnectedNode`
- Renamed `DeviceClass` to `DeviceType` and wired it into `DeviceDefinition`.
- Added basic I/O device implementations for first use cases:
  - `WhiteLedDevice` (on/off)
  - `RelayDevice` (on/off)
  - `ButtonDevice` (press/release events)
- Added/updated unit tests for host engine routing and basic I/O behavior.

## Why

- UUID identity enforces explicit unique IDs and avoids loose string typing.
- Template/instance split aligns with your preferred object model.
- `HostEngine` naming matches orchestration intent better.
- Protocol abstraction keeps communication open for MQTT/UART/socket/event/web APIs without locking to one transport.
