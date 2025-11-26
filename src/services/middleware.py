"""
Middleware for EventBus

Middleware = pipeline functions that process events before handlers.
Can modify events, block events, or log/validate events.
"""

from models.events import Event
from utils.logger import get_logger, LogCategory
from utils.serialization import Serializer

log = get_logger().for_category(LogCategory.SYSTEM)


def log_middleware(event: Event) -> Event:
    """
    Log all events for debugging

    Usage:
        event_bus.add_middleware(log_middleware)
    """
    # Format source (event.source is always an enum)
    source_str = Serializer.enum_to_str(event.source)

    # Format data compactly
    if 'delta' in event.data:
        data_str = f"delta={event.data['delta']}"
    else:
        data_str = str(event.data)

    log.info(
        f"Event: {event.type.name} from {source_str} | {data_str}"
    )
    return event
