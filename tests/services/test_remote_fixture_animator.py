"""RemoteFixtureAnimator: reproducing on the host what each remote fixture is
actually emitting, so the browser preview matches the real light."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.remote_fixture_animator import (
    BREATHE_CYCLE_DURATION_SECONDS,
    IDENTIFY_DURATION_SECONDS,
    RemoteFixtureAnimator,
)
from services.rig_service import RigService

CATALOG_YAML = """
catalog:
  drivers:
    - id: mosfet_driver_1ch
      name: "1-channel MOSFET dimmer"
      control_interface: ANALOG_PWM
      channels: [ch0]
    - id: addressable_data_output
      name: "Addressable data line"
      control_interface: ADDRESSABLE_DATA
      channels: [data]
  fixtures:
    - id: single_diode
      name: "Single diode"
      component_type: SINGLE_COLOR
      component_count: 1
      addressable_group_count: 1
    - id: addressable_strip
      name: "Addressable strip"
      component_type: ADDRESSABLE_PIXEL
      component_count: 4
      addressable_group_count: 4

rig:
  driver_instances:
    - id: desk_dimmer
      definition_id: mosfet_driver_1ch
      node_id: "AA:BB"
      label: "Desk dimmer"
      config: {channel_pins: {ch0: 23}}
  fixture_instances:
    - id: desk_diode
      definition_id: single_diode
      node_id: "AA:BB"
      label: "Desk diode"
      config:
        nominal_color: [255, 170, 80]
        bindings: [{module_instance_id: desk_dimmer, channel_name: ch0, role: SINGLE}]
  zones:
    - zone_id: desk
      display_name: "Desk"
      node_id: "AA:BB"
      device_instance_ids: [desk_diode]
      state: {color: [255, 255, 255], brightness: 100, is_on: true, render_mode: STATIC}
"""


@pytest.fixture
def rig(tmp_path: Path) -> RigService:
    catalog = tmp_path / "rig.yaml"
    catalog.write_text(CATALOG_YAML)
    return RigService(catalog_path=catalog, state_path=tmp_path / "rig.json")


@pytest.fixture
def animator(rig: RigService) -> RemoteFixtureAnimator:
    return RemoteFixtureAnimator(rig_service=rig)


def test_a_lit_diode_previews_in_its_declared_physical_colour(
    animator: RemoteFixtureAnimator,
) -> None:
    """The zone state says white, but the fitted diode is warm - the preview
    must show what the hardware can actually emit."""
    pixels = animator.compute_fixture_pixels(now=0.0)

    assert pixels["desk_diode"] == [(255, 170, 80)]


def test_a_fixture_previews_one_pixel_per_addressable_group(
    rig: RigService, animator: RemoteFixtureAnimator
) -> None:
    assert len(animator.compute_fixture_pixels(now=0.0)["desk_diode"]) == 1


def test_switching_off_previews_as_black(rig: RigService, animator: RemoteFixtureAnimator) -> None:
    rig.update_zone_state("desk", is_on=False)

    assert animator.compute_fixture_pixels(now=0.0)["desk_diode"] == [(0, 0, 0)]


def test_brightness_scales_the_preview(rig: RigService, animator: RemoteFixtureAnimator) -> None:
    rig.update_zone_state("desk", brightness=50)

    red, green, blue = animator.compute_fixture_pixels(now=0.0)["desk_diode"][0]

    assert (red, green, blue) < (255, 170, 80)
    assert red > 0


def test_breathe_preview_varies_over_the_cycle(
    rig: RigService, animator: RemoteFixtureAnimator
) -> None:
    """The preview must actually animate, matching the firmware's triangle wave
    rather than sitting at a fixed colour."""
    rig.update_zone_state("desk", render_mode="BREATHE")

    at_cycle_start = animator.compute_fixture_pixels(now=0.0)["desk_diode"][0]
    at_cycle_peak = animator.compute_fixture_pixels(
        now=BREATHE_CYCLE_DURATION_SECONDS / 2
    )["desk_diode"][0]

    assert at_cycle_start == (0, 0, 0)
    assert max(at_cycle_peak) > 200


def test_breathe_is_symmetric_around_the_peak(
    rig: RigService, animator: RemoteFixtureAnimator
) -> None:
    rig.update_zone_state("desk", render_mode="BREATHE")
    quarter = BREATHE_CYCLE_DURATION_SECONDS / 4

    rising = animator.compute_fixture_pixels(now=quarter)["desk_diode"][0]
    falling = animator.compute_fixture_pixels(now=quarter * 3)["desk_diode"][0]

    assert rising == falling


def test_identify_makes_the_preview_blink(animator: RemoteFixtureAnimator) -> None:
    animator.mark_identifying("AA:BB")

    # Sampling across a few blink intervals must produce both on and off frames.
    samples = {
        animator.compute_fixture_pixels(now=offset)["desk_diode"][0]
        for offset in (0.0, 0.16, 0.32, 0.48)
    }

    assert len(samples) > 1


def test_identify_stops_blinking_after_its_duration(animator: RemoteFixtureAnimator) -> None:
    import time

    animator.mark_identifying("AA:BB")
    settled = animator.compute_fixture_pixels(
        now=time.time() + IDENTIFY_DURATION_SECONDS + 1
    )

    assert settled["desk_diode"] == [(255, 170, 80)]
