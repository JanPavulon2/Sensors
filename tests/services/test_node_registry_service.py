from __future__ import annotations

import asyncio

import pytest

from services.event_bus import EventBus
from services.node_registry_service import NodeRegistryService


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def registry(event_bus: EventBus) -> NodeRegistryService:
    return NodeRegistryService(event_bus=event_bus, node_shared_secret="test-secret")


def test_register_new_node_returns_snapshot_with_generated_instance_id(registry: NodeRegistryService) -> None:
    snapshot = asyncio.run(
        registry.register_or_update_node(
            external_node_id="AA:BB:CC:DD:EE:FF",
            node_type="ESP32",
            address="10.0.0.5",
            command_port=8080,
            firmware="diuna-esp32-poc",
            capabilities=["render_output", "made_up"],
        )
    )

    assert snapshot.external_node_id == "AA:BB:CC:DD:EE:FF"
    assert snapshot.address == "10.0.0.5"
    assert snapshot.online is True
    assert snapshot.capabilities == ["render_output"]  # unknown capability filtered out


def test_register_existing_node_reuses_the_same_instance_id(registry: NodeRegistryService) -> None:
    first = asyncio.run(
        registry.register_or_update_node(
            external_node_id="AA:BB:CC:DD:EE:FF",
            node_type="ESP32",
            address="10.0.0.5",
            command_port=8080,
            firmware="diuna-esp32-poc",
            capabilities=[],
        )
    )
    second = asyncio.run(
        registry.register_or_update_node(
            external_node_id="AA:BB:CC:DD:EE:FF",
            node_type="ESP32",
            address="10.0.0.99",  # DHCP lease changed
            command_port=8080,
            firmware="diuna-esp32-poc",
            capabilities=[],
        )
    )

    assert first.instance_id == second.instance_id
    assert second.address == "10.0.0.99"


def test_get_node_returns_none_for_unknown_node(registry: NodeRegistryService) -> None:
    assert registry.get_node("unknown") is None


def test_list_nodes_returns_all_registered_nodes(registry: NodeRegistryService) -> None:
    asyncio.run(
        registry.register_or_update_node(
            external_node_id="AA:BB:CC:DD:EE:FF",
            node_type="ESP32",
            address="10.0.0.5",
            command_port=8080,
            firmware="diuna-esp32-poc",
            capabilities=[],
        )
    )
    asyncio.run(
        registry.register_or_update_node(
            external_node_id="11:22:33:44:55:66",
            node_type="ESP32",
            address="10.0.0.6",
            command_port=8080,
            firmware="diuna-esp32-poc",
            capabilities=[],
        )
    )

    nodes = registry.list_nodes()

    assert {n.external_node_id for n in nodes} == {"AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"}


def test_send_command_raises_for_unregistered_node(registry: NodeRegistryService) -> None:
    with pytest.raises(ValueError):
        asyncio.run(registry.send_command("unknown", "identify", {}))


def test_send_command_delivers_message_through_transport(registry: NodeRegistryService, monkeypatch: pytest.MonkeyPatch) -> None:
    delivered = []

    async def fake_send(destination_node, packet) -> None:
        delivered.append((destination_node.address, packet.message.name, packet.message.payload))

    monkeypatch.setattr(registry._transport, "send", fake_send)

    async def scenario() -> None:
        engine_task = asyncio.create_task(registry.run_engine_loop())
        await registry.register_or_update_node(
            external_node_id="AA:BB:CC:DD:EE:FF",
            node_type="ESP32",
            address="10.0.0.5",
            command_port=8080,
            firmware="diuna-esp32-poc",
            capabilities=[],
        )
        await registry.send_command("AA:BB:CC:DD:EE:FF", "identify", {"a": 1})
        await asyncio.sleep(0.05)  # let the HostEngine queue drain
        engine_task.cancel()

    asyncio.run(scenario())

    assert delivered == [("10.0.0.5", "identify", {"a": 1})]
