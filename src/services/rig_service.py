"""Rig Service - owns the driver/fixture catalog and this installation's actual
wiring, and persists the editable half to src/state/rig.json.

Two halves, per docs/architecture-vnext/01-naming-convention.md:

  catalog   Module / LightFixture / DeviceDefinition blueprints. What a thing
            IS. Hand-authored in src/config/rig.yaml, stable slug ids, the list
            the add/edit UI picks from. Not user-editable at runtime.

  rig       DeviceInstance records. What is ACTUALLY wired up: on which node, to
            which GPIO pins, with which diode fitted. Editable from the UI and
            persisted to rig.json, because a graphical add/edit interface cannot
            safely rewrite a hand-commented YAML file.

Device capabilities are never stored - they are derived from
(module control interface x fixture component type x channel bindings) by
core/capability_derivation.py, so they cannot drift from the hardware.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from core.capability_derivation import derive_fixture_capabilities, derive_zone_capabilities
from core.device_definition import DeviceDefinition
from core.device_instance import DeviceInstance
from core.hardware_control_interface import HardwareControlInterface
from core.light import ChannelBinding, ChannelRole, LightComponentType, LightFixture, WhiteProfile
from core.module import Module
from core.peripheral import Peripheral
from core.peripheral_type import PeripheralType
from core.port_definition import PortDefinition, PortDirection, SignalType
from models.color import Color
from models.domain.remote_zone import RemoteZone, RemoteZoneState
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ZONE)

SAVE_DEBOUNCE_SECONDS = 0.5


class RigValidationError(ValueError):
    """Raised when a rig edit would produce hardware that cannot exist."""


class RigService:
    def __init__(self, catalog_path: Path, state_path: Path):
        self._catalog_path = catalog_path
        self._state_path = state_path

        self._driver_definitions: Dict[str, DeviceDefinition] = {}
        self._fixture_definitions: Dict[str, DeviceDefinition] = {}
        self._modules: Dict[str, Module] = {}
        self._fixtures: Dict[str, LightFixture] = {}

        self._driver_instances: Dict[str, DeviceInstance] = {}
        self._fixture_instances: Dict[str, DeviceInstance] = {}
        self._zones: Dict[str, RemoteZone] = {}
        self._zone_states: Dict[str, RemoteZoneState] = {}

        self._save_task: Optional[asyncio.Task] = None

        self._load()

    # === Loading / persistence ===

    def _load(self) -> None:
        catalog_data = self._read_yaml(self._catalog_path)
        self._load_catalog(catalog_data.get("catalog", {}))

        if self._state_path.exists():
            self._load_rig(json.loads(self._state_path.read_text(encoding="utf-8")))
            log.info(f"Rig loaded from {self._state_path.name}")
        else:
            self._load_rig(catalog_data.get("rig", {}))
            log.info(f"Rig bootstrapped from {self._catalog_path.name} (no rig.json yet)")

    @staticmethod
    def _read_yaml(path: Path) -> dict:
        if not path.exists():
            log.warn(f"Rig catalog not found at {path} - starting with an empty catalog")
            return {}
        with open(path, "r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or {}

    def _load_catalog(self, catalog: dict) -> None:
        for entry in catalog.get("drivers", []):
            definition_id = entry["id"]
            control_interface = HardwareControlInterface[entry["control_interface"]]
            peripheral_type = (
                PeripheralType.MOSFET_CHANNEL
                if control_interface is HardwareControlInterface.ANALOG_PWM
                else PeripheralType.ARGB_LED
            )
            self._modules[definition_id] = Module(
                id=definition_id,
                name=entry["name"],
                control_interface=control_interface,
                peripherals=tuple(
                    Peripheral(id=name, name=name, peripheral_type=peripheral_type)
                    for name in entry.get("channels", [])
                ),
            )
            self._driver_definitions[definition_id] = DeviceDefinition(
                id=definition_id,
                name=entry["name"],
                ports=self._parse_ports(entry.get("ports", [])),
            )

        for entry in catalog.get("fixtures", []):
            definition_id = entry["id"]
            self._fixtures[definition_id] = LightFixture(
                id=definition_id,
                name=entry["name"],
                component_type=LightComponentType[entry["component_type"]],
                component_count=entry.get("component_count", 1),
                addressable_group_count=entry.get("addressable_group_count", 1),
                white_profile=(
                    WhiteProfile[entry["white_profile"]] if entry.get("white_profile") else None
                ),
            )
            self._fixture_definitions[definition_id] = DeviceDefinition(
                id=definition_id,
                name=entry["name"],
                ports=self._parse_ports(entry.get("ports", [])),
            )

    @staticmethod
    def _parse_ports(entries: List[dict]) -> tuple[PortDefinition, ...]:
        return tuple(
            PortDefinition(
                name=entry["name"],
                direction=PortDirection[entry["direction"]],
                signal_type=SignalType[entry["signal_type"]],
            )
            for entry in entries
        )

    def _load_rig(self, rig: dict) -> None:
        for entry in rig.get("driver_instances", []):
            self._driver_instances[entry["id"]] = self._to_instance(entry)

        for entry in rig.get("fixture_instances", []):
            self._fixture_instances[entry["id"]] = self._to_instance(entry)

        for entry in rig.get("zones", []):
            zone_id = entry["zone_id"]
            self._zones[zone_id] = RemoteZone(
                zone_id=zone_id,
                display_name=entry.get("display_name", zone_id),
                node_id=entry["node_id"],
                device_instance_ids=list(entry.get("device_instance_ids", [])),
                sync_group=entry.get("sync_group"),
            )
            self._zone_states[zone_id] = self._to_zone_state(entry.get("state", {}))

    @staticmethod
    def _to_instance(entry: dict) -> DeviceInstance:
        return DeviceInstance(
            id=entry["id"],
            definition_id=entry["definition_id"],
            node_id=entry["node_id"],
            label=entry.get("label", entry["id"]),
            config=dict(entry.get("config", {})),
        )

    @staticmethod
    def _to_zone_state(state: dict) -> RemoteZoneState:
        red, green, blue = state.get("color", [255, 255, 255])
        return RemoteZoneState(
            color=Color.from_rgb(red, green, blue),
            brightness=state.get("brightness", 100),
            is_on=state.get("is_on", True),
            render_mode=state.get("render_mode", "STATIC"),
        )

    def to_persistable_dict(self) -> dict:
        return {
            "driver_instances": [
                self._instance_to_dict(instance) for instance in self._driver_instances.values()
            ],
            "fixture_instances": [
                self._instance_to_dict(instance) for instance in self._fixture_instances.values()
            ],
            "zones": [
                {
                    "zone_id": zone.zone_id,
                    "display_name": zone.display_name,
                    "node_id": zone.node_id,
                    "device_instance_ids": list(zone.device_instance_ids),
                    "sync_group": zone.sync_group,
                    "state": {
                        "color": list(self._zone_states[zone.zone_id].color.to_rgb()),
                        "brightness": self._zone_states[zone.zone_id].brightness,
                        "is_on": self._zone_states[zone.zone_id].is_on,
                        "render_mode": self._zone_states[zone.zone_id].render_mode,
                    },
                }
                for zone in self._zones.values()
            ],
        }

    @staticmethod
    def _instance_to_dict(instance: DeviceInstance) -> dict:
        return {
            "id": instance.id,
            "definition_id": instance.definition_id,
            "node_id": instance.node_id,
            "label": instance.label,
            "config": dict(instance.config),
        }

    def save_now(self) -> None:
        """Write the editable half of the rig to disk immediately."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(self.to_persistable_dict(), indent=2), encoding="utf-8"
        )

    async def _debounced_save(self) -> None:
        await asyncio.sleep(SAVE_DEBOUNCE_SECONDS)
        try:
            self.save_now()
        except Exception as error:
            log.error(f"Failed to save rig state: {error}")

    def queue_save(self) -> None:
        """Debounced save - mirrors ApplicationStateService._queue_save() so
        rapid UI edits (a dragged brightness slider) don't thrash the disk."""
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (synchronous setup, tests) - persist directly.
            # Checked before building the coroutine so none is left unawaited.
            self.save_now()
            return

        self._save_task = asyncio.create_task(self._debounced_save())

    # === Catalog reads ===

    def list_driver_definitions(self) -> List[DeviceDefinition]:
        return list(self._driver_definitions.values())

    def list_fixture_definitions(self) -> List[DeviceDefinition]:
        return list(self._fixture_definitions.values())

    def get_module(self, definition_id: str) -> Optional[Module]:
        return self._modules.get(definition_id)

    def get_fixture(self, definition_id: str) -> Optional[LightFixture]:
        return self._fixtures.get(definition_id)

    # === Instance reads ===

    def list_driver_instances(self) -> List[DeviceInstance]:
        return list(self._driver_instances.values())

    def list_fixture_instances(self) -> List[DeviceInstance]:
        return list(self._fixture_instances.values())

    def get_fixture_instance(self, instance_id: str) -> Optional[DeviceInstance]:
        return self._fixture_instances.get(instance_id)

    def get_driver_instance(self, instance_id: str) -> Optional[DeviceInstance]:
        return self._driver_instances.get(instance_id)

    def list_zones(self) -> List[RemoteZone]:
        return list(self._zones.values())

    def get_zone(self, zone_id: str) -> Optional[RemoteZone]:
        return self._zones.get(zone_id)

    def get_zones_for_node(self, node_id: str) -> List[RemoteZone]:
        return [zone for zone in self._zones.values() if zone.node_id == node_id]

    def get_zone_state(self, zone_id: str) -> RemoteZoneState:
        if zone_id not in self._zone_states:
            raise RigValidationError(f"Unknown remote zone: {zone_id}")
        return self._zone_states[zone_id]

    # === Derived capabilities ===

    def bindings_for(self, fixture_instance: DeviceInstance) -> List[ChannelBinding]:
        return [
            ChannelBinding(
                module_instance_id=binding["module_instance_id"],
                channel_name=binding["channel_name"],
                role=ChannelRole[binding["role"]],
            )
            for binding in fixture_instance.config.get("bindings", [])
        ]

    def get_fixture_instance_capabilities(self, instance_id: str) -> set[str]:
        instance = self._fixture_instances.get(instance_id)
        if instance is None:
            raise RigValidationError(f"Unknown fixture instance: {instance_id}")

        fixture = self._fixtures.get(instance.definition_id)
        if fixture is None:
            raise RigValidationError(
                f"Fixture instance '{instance_id}' references unknown definition "
                f"'{instance.definition_id}'"
            )

        bindings = self.bindings_for(instance)
        module = self._module_for_bindings(bindings)
        if module is None:
            # Nothing wired up yet - it can still be switched, nothing more.
            return {"switch_binary"}

        return derive_fixture_capabilities(fixture, module, bindings)

    def _module_for_bindings(self, bindings: List[ChannelBinding]) -> Optional[Module]:
        for binding in bindings:
            driver_instance = self._driver_instances.get(binding.module_instance_id)
            if driver_instance is not None:
                return self._modules.get(driver_instance.definition_id)
        return None

    def get_zone_capabilities(self, zone_id: str) -> set[str]:
        zone = self._zones.get(zone_id)
        if zone is None:
            raise RigValidationError(f"Unknown remote zone: {zone_id}")

        return derive_zone_capabilities(
            self.get_fixture_instance_capabilities(instance_id)
            for instance_id in zone.device_instance_ids
        )

    # === Validation ===

    def _validate_fixture_instance(self, instance: DeviceInstance) -> None:
        if instance.definition_id not in self._fixtures:
            raise RigValidationError(
                f"Unknown fixture definition '{instance.definition_id}'. Known: "
                f"{sorted(self._fixtures)}"
            )

        for binding in self.bindings_for(instance):
            driver_instance = self._driver_instances.get(binding.module_instance_id)
            if driver_instance is None:
                raise RigValidationError(
                    f"Binding references unknown driver instance '{binding.module_instance_id}'"
                )
            if driver_instance.node_id != instance.node_id:
                raise RigValidationError(
                    f"Fixture '{instance.id}' is on node {instance.node_id} but its driver "
                    f"'{driver_instance.id}' is on node {driver_instance.node_id} - a fixture "
                    f"cannot be driven from a different node"
                )
            module = self._modules.get(driver_instance.definition_id)
            if module is None or not module.has_channel(binding.channel_name):
                raise RigValidationError(
                    f"Driver '{driver_instance.id}' has no channel '{binding.channel_name}'. "
                    f"Available: {list(module.channel_names()) if module else []}"
                )

    def _validate_driver_instance(self, instance: DeviceInstance) -> None:
        module = self._modules.get(instance.definition_id)
        if module is None:
            raise RigValidationError(
                f"Unknown driver definition '{instance.definition_id}'. Known: "
                f"{sorted(self._modules)}"
            )

        for channel_name in instance.config.get("channel_pins", {}):
            if not module.has_channel(channel_name):
                raise RigValidationError(
                    f"Driver definition '{module.id}' has no channel '{channel_name}'. "
                    f"Available: {list(module.channel_names())}"
                )

    # === Instance writes ===

    def upsert_driver_instance(self, instance: DeviceInstance) -> DeviceInstance:
        self._validate_driver_instance(instance)
        self._driver_instances[instance.id] = instance
        self.queue_save()
        return instance

    def upsert_fixture_instance(self, instance: DeviceInstance) -> DeviceInstance:
        self._validate_fixture_instance(instance)
        self._fixture_instances[instance.id] = instance
        self.queue_save()
        return instance

    def delete_fixture_instance(self, instance_id: str) -> None:
        if instance_id not in self._fixture_instances:
            raise RigValidationError(f"Unknown fixture instance: {instance_id}")

        del self._fixture_instances[instance_id]
        for zone in self._zones.values():
            if instance_id in zone.device_instance_ids:
                zone.device_instance_ids.remove(instance_id)
        self.queue_save()

    def delete_driver_instance(self, instance_id: str) -> None:
        if instance_id not in self._driver_instances:
            raise RigValidationError(f"Unknown driver instance: {instance_id}")

        dependents = [
            fixture_instance.id
            for fixture_instance in self._fixture_instances.values()
            if any(
                binding.module_instance_id == instance_id
                for binding in self.bindings_for(fixture_instance)
            )
        ]
        if dependents:
            raise RigValidationError(
                f"Driver '{instance_id}' still drives fixture(s) {dependents} - rebind or "
                f"delete them first"
            )

        del self._driver_instances[instance_id]
        self.queue_save()

    # === Zone writes ===

    def upsert_zone(self, zone: RemoteZone) -> RemoteZone:
        for instance_id in zone.device_instance_ids:
            instance = self._fixture_instances.get(instance_id)
            if instance is None:
                raise RigValidationError(f"Unknown fixture instance: {instance_id}")
            if instance.node_id != zone.node_id:
                raise RigValidationError(
                    f"Fixture '{instance_id}' is on node {instance.node_id}, but zone "
                    f"'{zone.zone_id}' is on node {zone.node_id}"
                )

        is_new = zone.zone_id not in self._zones
        self._zones[zone.zone_id] = zone
        if is_new:
            self._zone_states.setdefault(
                zone.zone_id, RemoteZoneState(color=Color.from_rgb(255, 255, 255))
            )
        self.queue_save()
        return zone

    def delete_zone(self, zone_id: str) -> None:
        if zone_id not in self._zones:
            raise RigValidationError(f"Unknown remote zone: {zone_id}")
        del self._zones[zone_id]
        self._zone_states.pop(zone_id, None)
        self.queue_save()

    def update_zone_state(self, zone_id: str, **changes: Any) -> RemoteZoneState:
        state = self.get_zone_state(zone_id)
        for field_name, value in changes.items():
            setattr(state, field_name, value)
        self.queue_save()
        return state
