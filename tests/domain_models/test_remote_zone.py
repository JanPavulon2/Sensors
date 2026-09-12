from pathlib import Path

from models.color import Color
from models.domain.remote_zone import RemoteZoneConfig, RemoteZoneState, load_remote_zone_configs


def test_remote_zone_state_defaults() -> None:
    state = RemoteZoneState(color=Color.from_rgb(255, 255, 255))

    assert state.brightness == 100
    assert state.is_on is True
    assert state.render_mode == "STATIC"


def test_load_remote_zone_configs_parses_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "esp32_zones.yaml"
    config_file.write_text(
        """
remote_zones:
  - node_id: "AA:BB:CC:DD:EE:FF"
    zone_label: "esp32_strip_1"
    display_name: "Workshop Strip"
    pixel_count: 30
    sync_group: "workshop"
  - node_id: "11:22:33:44:55:66"
    zone_label: "esp32_strip_2"
    pixel_count: 30
"""
    )

    configs = load_remote_zone_configs(config_file)

    assert configs == [
        RemoteZoneConfig(
            node_id="AA:BB:CC:DD:EE:FF",
            zone_label="esp32_strip_1",
            display_name="Workshop Strip",
            pixel_count=30,
            sync_group="workshop",
        ),
        RemoteZoneConfig(
            node_id="11:22:33:44:55:66",
            zone_label="esp32_strip_2",
            display_name="esp32_strip_2",
            pixel_count=30,
            sync_group=None,
        ),
    ]


def test_load_remote_zone_configs_returns_empty_list_when_file_missing(tmp_path: Path) -> None:
    assert load_remote_zone_configs(tmp_path / "does_not_exist.yaml") == []
