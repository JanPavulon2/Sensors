from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.capabilities import (
    DEVICE_CAPABILITIES,
    ESP32_LED_STRIP_DEVICE_CAPABILITIES,
    NODE_CAPABILITIES,
    split_known_node_capabilities,
)


def test_node_capabilities_contains_esp32_vocabulary() -> None:
    assert {"render_output", "command_execution", "telemetry_publish"} <= NODE_CAPABILITIES


def test_device_capabilities_contains_led_strip_vocabulary() -> None:
    assert {"addressable_pixels", "color_control_rgb"} <= DEVICE_CAPABILITIES


def test_esp32_led_strip_device_capabilities_are_known() -> None:
    assert set(ESP32_LED_STRIP_DEVICE_CAPABILITIES) <= DEVICE_CAPABILITIES


def test_split_known_node_capabilities_separates_unknown_entries() -> None:
    known, unknown = split_known_node_capabilities(["render_output", "made_up_capability"])

    assert known == ["render_output"]
    assert unknown == ["made_up_capability"]
