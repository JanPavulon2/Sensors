from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.node_command_router_device import NodeCommandRouterDevice


def test_add_target_creates_a_dedicated_output_port_per_node() -> None:
    router = NodeCommandRouterDevice()

    port_a = router.add_target("AA:BB:CC:DD:EE:FF")
    port_b = router.add_target("11:22:33:44:55:66")

    assert port_a.id != port_b.id
    assert router.get_target_port("AA:BB:CC:DD:EE:FF") is port_a
    assert router.get_target_port("11:22:33:44:55:66") is port_b


def test_get_target_port_returns_none_for_unknown_node() -> None:
    router = NodeCommandRouterDevice()

    assert router.get_target_port("unknown") is None
