"""Remote Fixture Animator - reproduces, on the host, exactly what each remote
fixture is currently emitting, so the browser can show remote lights the same
way it shows local ones.

Remote zones stream state rather than frames (the ESP32 renders its own pixels),
so there is no pixel feed coming back to preview. But the host already computes
the NTP-synced breathe phase for MultiNodeSyncBroadcaster, and it originates
every identify command itself - so it knows enough to render the same thing
locally with no extra WiFi traffic.

The maths here deliberately mirrors firmware/firmware/src/main.cpp:
  - computeSyncedBreatheBrightness(): triangle wave over the shared cycle,
    driven by wall-clock time so every node and this preview agree
  - updateIdentifyBlink(): square wave at IDENTIFY_BLINK_INTERVAL_MILLISECONDS
If either changes there, change it here too or the preview will drift.
"""

from __future__ import annotations

import time
from typing import Dict, List, Tuple

from models.color import Color
from services.rig_service import RigService
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.FRAME_MANAGER)

# Must match DEFAULT_BREATHE_CYCLE_DURATION_MILLISECONDS in the firmware.
BREATHE_CYCLE_DURATION_SECONDS = 2.4

# Must match IDENTIFY_BLINK_INTERVAL_MILLISECONDS / IDENTIFY_DURATION_MILLISECONDS.
IDENTIFY_BLINK_INTERVAL_SECONDS = 0.15
IDENTIFY_DURATION_SECONDS = 2.0

PixelList = List[Tuple[int, int, int]]


class RemoteFixtureAnimator:
    def __init__(self, rig_service: RigService):
        self.rig_service = rig_service
        self._identify_started_at_by_node_id: Dict[str, float] = {}

    def mark_identifying(self, node_id: str) -> None:
        """Called when an identify command is sent, so the preview blinks in
        step with the hardware for the same duration."""
        self._identify_started_at_by_node_id[node_id] = time.time()

    def _is_identifying(self, node_id: str, now: float) -> bool:
        started_at = self._identify_started_at_by_node_id.get(node_id)
        if started_at is None:
            return False
        if now - started_at > IDENTIFY_DURATION_SECONDS:
            del self._identify_started_at_by_node_id[node_id]
            return False
        return True

    @staticmethod
    def _breathe_brightness_fraction(now: float) -> float:
        """Triangle wave over the shared cycle, 0.0 -> 1.0 -> 0.0.

        Uses wall-clock time (not a local counter) for the same reason the
        firmware does: it is the one clock every node already agrees on.
        """
        position_in_cycle = (now % BREATHE_CYCLE_DURATION_SECONDS) / BREATHE_CYCLE_DURATION_SECONDS
        if position_in_cycle < 0.5:
            return position_in_cycle * 2.0
        return (1.0 - position_in_cycle) * 2.0

    @staticmethod
    def _is_identify_blink_on(now: float) -> bool:
        return int(now / IDENTIFY_BLINK_INTERVAL_SECONDS) % 2 == 0

    def compute_fixture_pixels(self, now: float | None = None) -> Dict[str, PixelList]:
        """Current output colour of every remote fixture, keyed by fixture
        instance id, expanded to that fixture's independently driven groups."""
        now = time.time() if now is None else now
        pixels_by_fixture_id: Dict[str, PixelList] = {}

        for zone in self.rig_service.list_zones():
            state = self.rig_service.get_zone_state(zone.zone_id)
            red, green, blue = self._zone_output_color(zone.node_id, state, now)

            for instance_id in zone.device_instance_ids:
                instance = self.rig_service.get_fixture_instance(instance_id)
                if instance is None:
                    continue

                fixture = self.rig_service.get_fixture(instance.definition_id)
                group_count = fixture.addressable_group_count if fixture else 1

                # A fixture whose diode colour is fixed shows that colour, not
                # whatever colour the zone state happens to hold - the hardware
                # cannot produce anything else.
                pixel = self._apply_nominal_color(instance, (red, green, blue))
                pixels_by_fixture_id[instance_id] = [pixel] * group_count

        return pixels_by_fixture_id

    def _zone_output_color(self, node_id: str, state, now: float) -> Tuple[int, int, int]:
        if self._is_identifying(node_id, now):
            return (255, 255, 255) if self._is_identify_blink_on(now) else (0, 0, 0)

        if not state.is_on:
            return (0, 0, 0)

        brightness = state.brightness
        if state.render_mode == "BREATHE":
            brightness = int(brightness * self._breathe_brightness_fraction(now))

        return state.color.with_brightness(brightness).to_rgb()

    @staticmethod
    def _apply_nominal_color(instance, rendered: Tuple[int, int, int]) -> Tuple[int, int, int]:
        nominal_color = instance.config.get("nominal_color")
        if not nominal_color:
            return rendered

        # Scale the declared physical colour by the rendered luminance, so a
        # warm-white diode previews as warm white dimming, never as blue.
        luminance = max(rendered) / 255.0
        return tuple(int(channel * luminance) for channel in nominal_color[:3])
