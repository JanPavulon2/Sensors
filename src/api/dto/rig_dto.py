"""Shared REST/Socket.IO serialization for rig entities.

Capabilities are always DERIVED here rather than read from storage, so a payload
can never claim hardware can do something it physically cannot.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.device_definition import DeviceDefinition
from core.device_instance import DeviceInstance
from core.light import LightFixture
from core.module import Module
from models.domain.remote_zone import RemoteZone, RemoteZoneState


def driver_definition_to_dict(definition: DeviceDefinition, module: Module) -> Dict[str, Any]:
    return {
        "id": definition.id,
        "name": definition.name,
        "control_interface": module.control_interface.name,
        "channels": list(module.channel_names()),
        "channel_count": module.channel_count,
    }


def fixture_definition_to_dict(definition: DeviceDefinition, fixture: LightFixture) -> Dict[str, Any]:
    return {
        "id": definition.id,
        "name": definition.name,
        "component_type": fixture.component_type.name,
        "component_count": fixture.component_count,
        "addressable_group_count": fixture.addressable_group_count,
        "is_individually_addressable": fixture.is_individually_addressable,
        "white_profile": fixture.white_profile.name if fixture.white_profile else None,
    }


def instance_to_dict(instance: DeviceInstance) -> Dict[str, Any]:
    return {
        "id": instance.id,
        "definition_id": instance.definition_id,
        "node_id": instance.node_id,
        "label": instance.label,
        "config": dict(instance.config),
    }


def fixture_instance_to_dict(
    instance: DeviceInstance,
    capabilities: set,
    fixture: LightFixture | None = None,
) -> Dict[str, Any]:
    data = instance_to_dict(instance)
    data["capabilities"] = sorted(capabilities)
    # Carried from the blueprint so the UI doesn't have to guess how many
    # pixels to preview, or cross-reference the catalog to find out.
    data["component_type"] = fixture.component_type.name if fixture else None
    data["component_count"] = fixture.component_count if fixture else 1
    data["addressable_group_count"] = fixture.addressable_group_count if fixture else 1
    return data


def zone_state_to_dict(state: RemoteZoneState) -> Dict[str, Any]:
    red, green, blue = state.color.to_rgb()
    return {
        "is_on": state.is_on,
        "brightness": state.brightness,
        "color": {"rgb": [red, green, blue]},
        "render_mode": state.render_mode,
    }


def zone_to_dict(
    zone: RemoteZone,
    state: RemoteZoneState,
    capabilities: set,
    is_in_sync: bool,
    fixtures: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "zone_id": zone.zone_id,
        "display_name": zone.display_name,
        "node_id": zone.node_id,
        "device_instance_ids": list(zone.device_instance_ids),
        "sync_group": zone.sync_group,
        "capabilities": sorted(capabilities),
        "in_sync": is_in_sync,
        "state": zone_state_to_dict(state),
        "fixtures": fixtures,
    }
