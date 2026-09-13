from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_service_container
from api.main import create_app
from models.domain.node import NodeSnapshot
from services.rig_service import RigService
from services.service_container import ServiceContainer


def empty_rig_service() -> RigService:
    """A rig with a catalog but nothing wired up, so node routes can be tested
    without dragging in any fixture configuration."""
    return RigService(
        catalog_path=Path(__file__).resolve().parents[2] / "src" / "config" / "rig.yaml",
        state_path=Path("/nonexistent/rig.json"),
    )


class FakeNodeRegistryService:
    def __init__(self) -> None:
        self.registered: List[Dict[str, Any]] = []
        self.sent_commands: List[Dict[str, Any]] = []
        self._snapshot = NodeSnapshot(
            instance_id="11111111-1111-1111-1111-111111111111",
            external_node_id="AA:BB:CC:DD:EE:FF",
            node_type="ESP32",
            address="10.0.0.5",
            command_port=8080,
            firmware="diuna-esp32-poc",
            capabilities=["render_output"],
            online=True,
            last_seen=datetime.now(timezone.utc),
        )

    async def register_or_update_node(self, **kwargs) -> NodeSnapshot:
        self.registered.append(kwargs)
        return self._snapshot

    def get_node(self, external_node_id: str):
        return self._snapshot if external_node_id == self._snapshot.external_node_id else None

    def list_nodes(self) -> List[NodeSnapshot]:
        return [self._snapshot]

    async def send_command(self, external_node_id: str, command_name: str, payload: dict) -> None:
        if external_node_id != self._snapshot.external_node_id:
            raise ValueError(f"Unknown node: {external_node_id}")
        self.sent_commands.append({"node": external_node_id, "name": command_name, "payload": payload})


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # NODE_SHARED_SECRET is read from the environment once at import time
    # (module-level constant), so monkeypatch.setenv() here would be too
    # late - the module is already imported by test collection. Patch the
    # already-resolved constant directly instead.
    monkeypatch.setattr("api.routes.nodes.NODE_SHARED_SECRET", "test-secret")

    fake_registry = FakeNodeRegistryService()
    app = create_app()

    async def fake_get_service_container() -> ServiceContainer:
        container = AsyncMock(spec=ServiceContainer)
        container.node_registry_service = fake_registry
        container.rig_service = empty_rig_service()
        container.remote_fixture_animator = MagicMock()
        return container

    app.dependency_overrides[get_service_container] = fake_get_service_container
    test_client = TestClient(app)
    test_client.fake_registry = fake_registry  # type: ignore[attr-defined]
    return test_client


def test_heartbeat_rejects_missing_secret(client: TestClient) -> None:
    response = client.post(
        "/api/v1/nodes/heartbeat",
        json={"node_id": "AA:BB:CC:DD:EE:FF", "node_type": "ESP32", "address": "10.0.0.5", "firmware": "poc"},
    )

    assert response.status_code == 401


def test_heartbeat_accepts_correct_secret(client: TestClient) -> None:
    response = client.post(
        "/api/v1/nodes/heartbeat",
        json={
            "node_id": "AA:BB:CC:DD:EE:FF",
            "node_type": "ESP32",
            "address": "10.0.0.5",
            "command_port": 8080,
            "firmware": "poc",
            "capabilities": ["render_output"],
        },
        headers={"X-Node-Secret": "test-secret"},
    )

    assert response.status_code == 200
    assert client.fake_registry.registered[0]["external_node_id"] == "AA:BB:CC:DD:EE:FF"  # type: ignore[attr-defined]


def test_list_nodes_returns_registered_nodes(client: TestClient) -> None:
    response = client.get("/api/v1/nodes")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["nodes"][0]["external_node_id"] == "AA:BB:CC:DD:EE:FF"


def test_get_node_404_for_unknown_node(client: TestClient) -> None:
    response = client.get("/api/v1/nodes/unknown")

    assert response.status_code == 404


def test_get_node_derives_device_capabilities_from_what_is_wired_to_it(client: TestClient) -> None:
    """Capabilities come from the rig, not from the node's type. The node in
    this fixture has nothing attached, so it advertises nothing."""
    response = client.get("/api/v1/nodes/AA:BB:CC:DD:EE:FF")

    assert response.status_code == 200
    assert response.json()["device_capabilities"] == []
    assert response.json()["zone_ids"] == []


def test_send_command_dispatches_to_registry(client: TestClient) -> None:
    response = client.post(
        "/api/v1/nodes/AA:BB:CC:DD:EE:FF/command",
        json={"name": "identify", "payload": {}},
    )

    assert response.status_code == 204
    assert client.fake_registry.sent_commands == [  # type: ignore[attr-defined]
        {"node": "AA:BB:CC:DD:EE:FF", "name": "identify", "payload": {}}
    ]


def test_send_command_404_for_unknown_node(client: TestClient) -> None:
    response = client.post(
        "/api/v1/nodes/unknown/command",
        json={"name": "identify", "payload": {}},
    )

    assert response.status_code == 404
