from api.dto.node_snapshot_dto import node_snapshot_to_dict
from models.events import EventType
from models.events.node_events import NodeSnapshotUpdatedEvent
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def register_node_broadcaster(sio, services):
    """
    Registers EventBus subscription for node snapshot updates.
    Broadcasts remote node (ESP32) state changes to all connected clients.
    """

    async def on_node_snapshot_updated(event: NodeSnapshotUpdatedEvent) -> None:
        await sio.emit("node:snapshot", node_snapshot_to_dict(event.snapshot))

    services.event_bus.subscribe(
        EventType.NODE_SNAPSHOT_UPDATED,
        on_node_snapshot_updated,
    )

    log.info("Node broadcaster registered with EventBus")
