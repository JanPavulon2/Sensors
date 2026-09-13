"""Capability vocabulary shared across node/device registration.

Mirrors docs/architecture-vnext/04-capabilities.md - keep both in sync.
"""

from __future__ import annotations

NODE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "render_output",
        "input_capture",
        "telemetry_publish",
        "command_execution",
        "local_automation",
        "storage_local",
    }
)

DEVICE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "switch_binary",
        "dimming",
        "color_control_rgb",
        "color_control_rgbw",
        "addressable_pixels",
        "sensor_read_temperature",
        "sensor_read_humidity",
        "sound_output",
        "display_output",
    }
)

# NOTE: there is deliberately no hardcoded per-node-type device capability list
# here any more. Device capabilities are derived from the actual driver module +
# light fixture + channel bindings - see core/capability_derivation.py. The old
# ESP32_LED_STRIP_DEVICE_CAPABILITIES constant claimed every ESP32 drove an
# addressable RGB strip, which was false for MOSFET-dimmed fixtures.


def split_known_node_capabilities(capabilities: list[str]) -> tuple[list[str], list[str]]:
    """Splits a heartbeat's reported capabilities into (known, unknown) against
    NODE_CAPABILITIES, so callers can log/reject unrecognized entries without
    hard-failing the heartbeat."""
    known = [capability for capability in capabilities if capability in NODE_CAPABILITIES]
    unknown = [capability for capability in capabilities if capability not in NODE_CAPABILITIES]
    return known, unknown
