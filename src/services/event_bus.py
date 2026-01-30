"""
Event Bus - Central event routing system

Implements pub-sub pattern:
- Publishers: publish(event)
- Subscribers: subscribe(event_type, handler, priority, filter_fn)
- Middleware: add_middleware(middleware_fn)
"""

import asyncio
from typing import Callable, List, Dict, Optional, TypeVar, Any, Deque
from dataclasses import dataclass
from collections import deque
from models.events import Event, EventType
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.EVENT)

TEvent = TypeVar('TEvent', bound=Event)


@dataclass
class EventHandler:
    """Event handler registration"""
    handler: Callable[[Any], None]  # Stored as Any - type erasure is necessary
    priority: int
    filter_fn: Optional[Callable[[Any], bool]]  # Type erasure necessary here too


class EventBus:
    """
    Central event bus for pub-sub event handling

    Features:
    - Priority-based handler execution (high priority first)
    - Per-handler filtering (fine-grained control)
    - Middleware pipeline (logging, blocking, rate limiting)
    - Async/sync handler support (auto-detected)
    - Fault tolerance (one handler crash doesn't stop others)

    Example:
        bus = EventBus()

        # Subscribe
        bus.subscribe(
            EventType.ENCODER_ROTATE,
            handler_fn,
            priority=10,
            filter_fn=lambda e: e.source == "selector"
        )

        # Publish
        event = EncoderRotateEvent("selector", 1)
        await bus.publish(event)
    """

    _instance: Optional["EventBus"] = None

    @classmethod
    def instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Handlers organized by event type
        self._handlers: Dict[EventType, List[EventHandler]] = {}

        # Middleware pipeline (applied in registration order)
        self._middleware: List[Callable[[Event], Optional[Event]]] = []

        # Event history (circular buffer for debugging/undo)
        # Using deque with maxlen for O(1) auto-eviction of old events
        self._event_history: Deque[Event] = deque(maxlen=100)

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[TEvent], None],
        priority: int = 0,
        filter_fn: Optional[Callable[[TEvent], bool]] = None
    ) -> None:
        """
        Subscribe to event type

        Args:
            event_type: Which events to listen for
            handler: Function to call (can be async or sync)
                     Can be strongly typed to specific event type (e.g., KeyboardKeyPressEvent)
            priority: Execution priority (higher = called first, default: 0)
            filter_fn: Optional filter (return True = handle, False = skip)

        Example:
            # Strongly typed handler
            def _on_keyboard(event: KeyboardKeyPressEvent) -> None:
                print(f"Key: {event.key}")

            # Only handle selector rotations when edit mode is ON
            bus.subscribe(
                EventType.ENCODER_ROTATE,
                self._on_encoder_rotate,
                priority=10,
                filter_fn=lambda e: e.source == "selector" and self.edit_mode
            )
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        handler_entry = EventHandler(handler, priority, filter_fn)
        self._handlers[event_type].append(handler_entry)

        # Sort by priority (descending - highest first)
        self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)

        log.info(
            "Event handler subscribed",
            event_type=event_type.name,
            handler=handler.__name__,
            priority=priority
        )

    def add_middleware(self, middleware: Callable[[Event], Optional[Event]]) -> None:
        """
        Add middleware to event processing pipeline

        Middleware can:
        - Modify events (return modified event)
        - Block events (return None)
        - Log/validate events

        Middleware runs in registration order (FIFO).

        Args:
            middleware: Function that takes Event, returns Event or None

        Example:
            def log_middleware(event):
                print(f"Event: {event.type.name}")
                return event  # Pass through

            bus.add_middleware(log_middleware)
        """
        self._middleware.append(middleware)
        log.info(
            "Middleware registered",
            middleware=middleware.__name__
        )

    async def publish(self, event: Event) -> None:
        """
        Publish event to all subscribers

        Flow:
        1. Apply middleware (can modify or block event)
        2. Save to event history
        3. Lookup handlers for event type
        4. Execute handlers by priority (high → low)
        5. Apply per-handler filters
        6. Handle async/sync handlers transparently
        7. Catch and log handler exceptions (fault tolerance)

        Args:
            event: Event to publish

        Example:
            event = EncoderRotateEvent("selector", 1)
            await bus.publish(event)
        """
        log.debug("Event: ", event_type=event.type.name)
        
        # Apply middleware pipeline
        for middleware in self._middleware:
            processed_event = middleware(event)
            if processed_event is None:
                # Event blocked by middleware
                return
            event = processed_event

        # Save to history (auto-evicts oldest event when full via deque maxlen)
        self._event_history.append(event)

        # Get handlers for this event type
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            log.info(
                f"No event handlers registered for event {event.type.name}")
            return

        # Execute handlers by priority
        for handler_entry in handlers:
            # Apply per-handler filter
            if handler_entry.filter_fn and not handler_entry.filter_fn(event):
                continue

            try:
                # Handle async/sync transparently
                if asyncio.iscoroutinefunction(handler_entry.handler):
                    await handler_entry.handler(event)
                else:
                    handler_entry.handler(event)
            except Exception as e:
                log.error(
                    f"Event handler failed: {handler_entry.handler.__name__} for {event.type.name}",
                    exc_info=True,
                    handler=handler_entry.handler.__name__,
                    event_type=event.type.name
                )
                # Continue to next handler (fault tolerance)

    def get_event_history(self, limit: int = 10) -> List[Event]:
        """
        Get recent events from history

        Args:
            limit: Number of recent events to return

        Returns:
            List of recent events (newest last)
        """
        return list(self._event_history)[-limit:]

    def clear_history(self) -> None:
        """Clear event history"""
        self._event_history.clear()
