from models.color import Color
from models.domain.remote_zone import RemoteZone, RemoteZoneState


def test_remote_zone_state_defaults() -> None:
    state = RemoteZoneState(color=Color.from_rgb(255, 255, 255))

    assert state.brightness == 100
    assert state.is_on is True
    assert state.render_mode == "STATIC"


def test_remote_zone_defaults_to_no_devices_and_no_sync_group() -> None:
    zone = RemoteZone(zone_id="desk", display_name="Desk", node_id="AA:BB")

    assert zone.device_instance_ids == []
    assert zone.sync_group is None


def test_remote_zone_ids_are_free_form_strings() -> None:
    """Unlike the local ZoneID enum - this is what makes remote zones
    creatable at runtime from the UI."""
    zone = RemoteZone(zone_id="a zone created at 12:04", display_name="Ad hoc", node_id="AA:BB")

    assert zone.zone_id == "a zone created at 12:04"
