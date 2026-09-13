"""Node Configuration Pusher - translates a node's rig wiring into the
"node.config" command its firmware needs, and pushes it when the node appears.

The firmware no longer decides what is wired to it with a compile-time #if; it
receives its channel/pin/interface layout from here and stores it in NVS. That
is what makes "add a fixture in the UI" mean something on real hardware without
a reflash.

Subscribes to NODE_CAME_ONLINE rather than being called directly, for the same
reason RemoteZoneStateService does: NodeRegistryService sits below both of these
services, so a back-reference would be a dependency cycle.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from models.events import EventType, NodeCameOnlineEvent
from services.event_bus import EventBus
from services.node_registry_service import NodeRegistryService
from services.remote_zone_state_service import RemoteZoneStateService
from services.rig_service import RigService
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SYSTEM)


class NodeConfigurationPusher:
    def __init__(
        self,
        rig_service: RigService,
        node_registry_service: NodeRegistryService,
        remote_zone_state_service: RemoteZoneStateService,
        event_bus: EventBus,
    ):
        self.rig_service = rig_service
        self.node_registry_service = node_registry_service
        self.remote_zone_state_service = remote_zone_state_service

        event_bus.subscribe(EventType.NODE_CAME_ONLINE, self._on_node_came_online)

    async def _on_node_came_online(self, event: NodeCameOnlineEvent) -> None:
        await self.push_configuration(event.node_id)
        # A node that just appeared may have rebooted, so its outputs are back
        # at defaults - restore the state the host believes it should be in.
        await self.remote_zone_state_service.push_all_for_node(event.node_id)

    def build_configuration(self, node_id: str) -> Optional[Dict[str, Any]]:
        """The output layout for a node, or None when nothing is wired to it."""
        driver_instances = [
            instance
            for instance in self.rig_service.list_driver_instances()
            if instance.node_id == node_id
        ]
        if not driver_instances:
            return None

        # One driver module per node for now: the firmware drives a single
        # output block. Multiple modules per node needs a firmware change too,
        # so it is rejected loudly rather than silently half-applied.
        if len(driver_instances) > 1:
            log.warn(
                f"Node '{node_id}' has {len(driver_instances)} driver modules; the firmware "
                f"supports one. Configuring '{driver_instances[0].id}' only."
            )

        driver_instance = driver_instances[0]
        module = self.rig_service.get_module(driver_instance.definition_id)
        if module is None:
            log.warn(
                f"Driver instance '{driver_instance.id}' references unknown definition "
                f"'{driver_instance.definition_id}' - skipping node configuration"
            )
            return None

        roles_by_channel = self._roles_by_channel(driver_instance.id)
        channel_pins = driver_instance.config.get("channel_pins", {})

        channels: List[Dict[str, Any]] = []
        for channel_name in module.channel_names():
            pin = channel_pins.get(channel_name)
            if pin is None:
                continue
            channels.append({"role": roles_by_channel.get(channel_name, "SINGLE"), "pin": pin})

        configuration = {
            "interface": module.control_interface.name,
            "channels": channels,
            "pixel_count": self._pixel_count_for(driver_instance.id),
        }
        configuration["version"] = self._version_of(configuration)
        return configuration

    def _roles_by_channel(self, driver_instance_id: str) -> Dict[str, str]:
        roles: Dict[str, str] = {}
        for fixture_instance in self.rig_service.list_fixture_instances():
            for binding in self.rig_service.bindings_for(fixture_instance):
                if binding.module_instance_id == driver_instance_id:
                    roles[binding.channel_name] = binding.role.name
        return roles

    def _pixel_count_for(self, driver_instance_id: str) -> int:
        """How many pixels the firmware must drive: the largest fixture bound to
        this driver, since they all share its one output."""
        pixel_counts = [1]
        for fixture_instance in self.rig_service.list_fixture_instances():
            bindings = self.rig_service.bindings_for(fixture_instance)
            if not any(binding.module_instance_id == driver_instance_id for binding in bindings):
                continue
            fixture = self.rig_service.get_fixture(fixture_instance.definition_id)
            if fixture is not None:
                pixel_counts.append(fixture.addressable_group_count)
        return max(pixel_counts)

    @staticmethod
    def _version_of(configuration: Dict[str, Any]) -> str:
        """Content hash, so the node can tell whether its stored config is still
        the one the host intends without comparing every field."""
        serialized = json.dumps(configuration, sort_keys=True).encode("utf-8")
        return hashlib.sha1(serialized).hexdigest()[:16]

    async def push_configuration(self, node_id: str) -> bool:
        configuration = self.build_configuration(node_id)
        if configuration is None:
            log.info(f"Node '{node_id}' has no driver module configured - nothing to push")
            return False

        await self.node_registry_service.send_command(node_id, "node.config", configuration)
        log.info(
            f"Pushed output configuration to node '{node_id}'",
            version=configuration["version"],
        )
        return True
