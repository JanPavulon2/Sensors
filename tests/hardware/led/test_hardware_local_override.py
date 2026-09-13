"""Tests for the optional, gitignored per-machine hardware override.

src/config/hardware.yaml is committed and describes the Raspberry Pi 4 rig at
home. The Pi 5 development board has different hardware wired to it, and the
same git checkout has to run correctly on both without anyone editing a
tracked file. hardware.local.yaml exists only on the machine that needs it.
"""

import pytest
import yaml

from managers.config_manager import (
    LOCAL_HARDWARE_OVERRIDE_FILENAME,
    apply_local_hardware_override,
)


def test_absent_override_file_leaves_the_configuration_untouched(tmp_path):
    """The Raspberry Pi 4 case: no override file, so nothing may change."""
    merged = {
        "led_strips": [{"id": "MAIN_12V", "gpio": 18, "count": 51}],
        "zones": [{"id": "FLOOR"}],
    }
    original = {key: value for key, value in merged.items()}

    result = apply_local_hardware_override(merged, config_dir=tmp_path)

    assert result == original


def test_override_file_replaces_the_led_strips_it_declares(tmp_path):
    """The Pi 5 case: one test strip on SPI instead of two PWM chains."""
    (tmp_path / LOCAL_HARDWARE_OVERRIDE_FILENAME).write_text(
        yaml.safe_dump(
            {
                "led_strips": [
                    {
                        "id": "AUX_5V",
                        "gpio": 10,
                        "driver": "spi",
                        "type": "WS2812_5V",
                        "color_order": "GRB",
                        "count": 30,
                        "voltage": 5,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    merged = {
        "led_strips": [
            {"id": "MAIN_12V", "gpio": 18, "count": 51},
            {"id": "AUX_5V", "gpio": 19, "count": 68},
        ],
        "zones": [{"id": "FLOOR"}],
    }

    result = apply_local_hardware_override(merged, config_dir=tmp_path)

    assert len(result["led_strips"]) == 1
    assert result["led_strips"][0]["driver"] == "spi"
    assert result["led_strips"][0]["gpio"] == 10
    # Keys the override does not mention must survive untouched.
    assert result["zones"] == [{"id": "FLOOR"}]


def test_empty_override_file_is_treated_as_no_override(tmp_path):
    (tmp_path / LOCAL_HARDWARE_OVERRIDE_FILENAME).write_text("", encoding="utf-8")
    merged = {"led_strips": [{"id": "MAIN_12V", "gpio": 18}]}

    result = apply_local_hardware_override(merged, config_dir=tmp_path)

    assert result["led_strips"] == [{"id": "MAIN_12V", "gpio": 18}]
