"""Rig endpoints - the driver/fixture catalog, this installation's actual
wiring, and remote zone control.

Replaces the old /nodes/{id}/zones* surface. A zone is addressed by its own id
rather than by the node it happens to live on, because where a zone renders is a
property of the zone, not part of its identity.

Capabilities in every response are derived from the hardware
(core/capability_derivation.py), never stored - see src/services/rig_service.py.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_service_container
from api.dto.rig_dto import (
    driver_definition_to_dict,
    fixture_definition_to_dict,
    fixture_instance_to_dict,
    instance_to_dict,
    zone_state_to_dict,
    zone_to_dict,
)
from api.schemas.node import (
    SetRemoteZoneBrightnessRequest,
    SetRemoteZoneColorRequest,
    SetRemoteZoneIsOnRequest,
    SetRemoteZoneRenderModeRequest,
    UpsertDriverInstanceRequest,
    UpsertFixtureInstanceRequest,
    UpsertRemoteZoneRequest,
)
from core.device_instance import DeviceInstance
from models.color import Color
from models.domain.remote_zone import RemoteZone
from services.rig_service import RigValidationError
from services.service_container import ServiceContainer
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)

router = APIRouter(prefix="/rig", tags=["Rig"])


def _bad_request(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _build_zone_payload(services: ServiceContainer, zone: RemoteZone) -> Dict[str, Any]:
    rig = services.rig_service
    state_service = services.remote_zone_state_service

    fixtures = []
    for instance_id in zone.device_instance_ids:
        instance = rig.get_fixture_instance(instance_id)
        if instance is None:
            continue
        fixtures.append(
            fixture_instance_to_dict(
                instance,
                rig.get_fixture_instance_capabilities(instance_id),
                rig.get_fixture(instance.definition_id),
            )
        )

    return zone_to_dict(
        zone=zone,
        state=rig.get_zone_state(zone.zone_id),
        capabilities=rig.get_zone_capabilities(zone.zone_id),
        is_in_sync=state_service.is_in_sync(zone.zone_id),
        fixtures=fixtures,
    )


# === Catalog ===


@router.get("/catalog")
async def get_catalog(services: ServiceContainer = Depends(get_service_container)) -> Dict[str, Any]:
    """Blueprints the add/edit UI picks from. Read-only at runtime."""
    rig = services.rig_service
    return {
        "drivers": [
            driver_definition_to_dict(definition, rig.get_module(definition.id))
            for definition in rig.list_driver_definitions()
        ],
        "fixtures": [
            fixture_definition_to_dict(definition, rig.get_fixture(definition.id))
            for definition in rig.list_fixture_definitions()
        ],
    }


# === Driver instances ===


@router.get("/drivers")
async def list_driver_instances(
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    instances = services.rig_service.list_driver_instances()
    return {"drivers": [instance_to_dict(instance) for instance in instances]}


@router.put("/drivers/{instance_id}")
async def upsert_driver_instance(
    instance_id: str,
    request: UpsertDriverInstanceRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    try:
        instance = services.rig_service.upsert_driver_instance(
            DeviceInstance(
                id=instance_id,
                definition_id=request.definition_id,
                node_id=request.node_id,
                label=request.label,
                config={"channel_pins": dict(request.channel_pins)},
            )
        )
    except RigValidationError as error:
        raise _bad_request(error)

    return instance_to_dict(instance)


@router.delete("/drivers/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_driver_instance(
    instance_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    try:
        services.rig_service.delete_driver_instance(instance_id)
    except RigValidationError as error:
        raise _bad_request(error)


# === Fixture instances ===


@router.get("/fixtures")
async def list_fixture_instances(
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    rig = services.rig_service
    return {
        "fixtures": [
            fixture_instance_to_dict(
                instance,
                rig.get_fixture_instance_capabilities(instance.id),
                rig.get_fixture(instance.definition_id),
            )
            for instance in rig.list_fixture_instances()
        ]
    }


@router.put("/fixtures/{instance_id}")
async def upsert_fixture_instance(
    instance_id: str,
    request: UpsertFixtureInstanceRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    config: Dict[str, Any] = {
        "bindings": [
            {
                "module_instance_id": binding.module_instance_id,
                "channel_name": binding.channel_name,
                "role": binding.role.upper(),
            }
            for binding in request.bindings
        ]
    }
    if request.nominal_color is not None:
        config["nominal_color"] = list(request.nominal_color)
    if request.white_profile is not None:
        config["white_profile"] = request.white_profile.upper()

    try:
        instance = services.rig_service.upsert_fixture_instance(
            DeviceInstance(
                id=instance_id,
                definition_id=request.definition_id,
                node_id=request.node_id,
                label=request.label,
                config=config,
            )
        )
        capabilities = services.rig_service.get_fixture_instance_capabilities(instance_id)
    except (RigValidationError, KeyError) as error:
        raise _bad_request(error)

    return fixture_instance_to_dict(
        instance, capabilities, services.rig_service.get_fixture(instance.definition_id)
    )


@router.delete("/fixtures/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fixture_instance(
    instance_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    try:
        services.rig_service.delete_fixture_instance(instance_id)
    except RigValidationError as error:
        raise _not_found(str(error))


# === Zones ===


@router.get("/zones")
async def list_zones(services: ServiceContainer = Depends(get_service_container)) -> Dict[str, Any]:
    zones = services.rig_service.list_zones()
    return {"zones": [_build_zone_payload(services, zone) for zone in zones]}


@router.get("/zones/{zone_id}")
async def get_zone(
    zone_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    zone = services.rig_service.get_zone(zone_id)
    if zone is None:
        raise _not_found(f"Unknown remote zone: {zone_id}")
    return _build_zone_payload(services, zone)


@router.put("/zones/{zone_id}")
async def upsert_zone(
    zone_id: str,
    request: UpsertRemoteZoneRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    try:
        zone = services.rig_service.upsert_zone(
            RemoteZone(
                zone_id=zone_id,
                display_name=request.display_name,
                node_id=request.node_id,
                device_instance_ids=list(request.device_instance_ids),
                sync_group=request.sync_group,
            )
        )
    except RigValidationError as error:
        raise _bad_request(error)

    return _build_zone_payload(services, zone)


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    try:
        services.rig_service.delete_zone(zone_id)
    except RigValidationError as error:
        raise _not_found(str(error))


# === Zone state ===


@router.get("/zones/{zone_id}/state")
async def get_zone_state(
    zone_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    try:
        return zone_state_to_dict(services.rig_service.get_zone_state(zone_id))
    except RigValidationError as error:
        raise _not_found(str(error))


@router.put("/zones/{zone_id}/color", status_code=status.HTTP_204_NO_CONTENT)
async def set_zone_color(
    zone_id: str,
    request: SetRemoteZoneColorRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    _require_capability(services, zone_id, "color_control_rgb")

    color_request = request.color
    if color_request.mode == "PRESET" and color_request.preset_name:
        color = Color.from_preset(color_request.preset_name, services.color_manager)
    else:
        color = Color.from_request(color_request)

    try:
        await services.remote_zone_state_service.set_color(zone_id, color)
    except (RigValidationError, ValueError) as error:
        raise _not_found(str(error))


@router.put("/zones/{zone_id}/brightness", status_code=status.HTTP_204_NO_CONTENT)
async def set_zone_brightness(
    zone_id: str,
    request: SetRemoteZoneBrightnessRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    _require_capability(services, zone_id, "dimming")
    try:
        await services.remote_zone_state_service.set_brightness(zone_id, request.brightness)
    except (RigValidationError, ValueError) as error:
        raise _not_found(str(error))


@router.put("/zones/{zone_id}/is-on", status_code=status.HTTP_204_NO_CONTENT)
async def set_zone_is_on(
    zone_id: str,
    request: SetRemoteZoneIsOnRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    try:
        await services.remote_zone_state_service.set_is_on(zone_id, request.is_on)
    except (RigValidationError, ValueError) as error:
        raise _not_found(str(error))


@router.put("/zones/{zone_id}/render-mode", status_code=status.HTTP_204_NO_CONTENT)
async def set_zone_render_mode(
    zone_id: str,
    request: SetRemoteZoneRenderModeRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    try:
        await services.remote_zone_state_service.set_render_mode(zone_id, request.render_mode)
    except RigValidationError as error:
        raise _not_found(str(error))
    except ValueError as error:
        raise _bad_request(error)


def _require_capability(services: ServiceContainer, zone_id: str, capability: str) -> None:
    """Reject control the hardware physically cannot perform - asking a
    MOSFET-dimmed white diode for a colour is a client bug, not a 204."""
    try:
        capabilities = services.rig_service.get_zone_capabilities(zone_id)
    except RigValidationError as error:
        raise _not_found(str(error))

    if capability not in capabilities:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Zone '{zone_id}' does not support '{capability}'. It can: {sorted(capabilities)}",
        )
