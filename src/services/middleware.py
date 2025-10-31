"""
Middleware for EventBus

Middleware = pipeline functions that process events before handlers.
Can modify events, block events, or log/validate events.
"""

from models.events import Event
from utils.logger import get_logger, LogCategory

log = get_logger()


def log_middleware(event: Event) -> Event:
    """
    Log all events for debugging

    Usage:
        event_bus.add_middleware(log_middleware)
    """
    # Format source (handle both enum and string)
    source_str = event.source.name if hasattr(event.source, 'name') else str(event.source)

    log.debug(
        LogCategory.SYSTEM,
        f"EVENT: {event.type.name}",
        source=source_str,
        data=event.data
    )
    return event
