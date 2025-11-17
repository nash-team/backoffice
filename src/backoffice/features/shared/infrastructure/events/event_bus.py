"""Event bus for publishing and subscribing to domain events."""

import asyncio
import logging
from collections import defaultdict

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent
from backoffice.features.shared.infrastructure.events.event_handler import EventHandler

logger = logging.getLogger(__name__)


class EventBus:
    """In-memory event bus for publish/subscribe pattern.

    Supports registering handlers for specific event types and publishing
    events to all registered handlers. Handlers are executed asynchronously.

    Thread-safe for concurrent event publishing.
    """

    def __init__(self):
        """Initialize event bus with empty handler registry."""
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: Type of event to handle
            handler: Handler instance to register
        """
        self._handlers[event_type].append(handler)
        logger.info(f"📬 Subscribed {handler.__class__.__name__} to {event_type.__name__}")

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers.

        Handlers are executed asynchronously and in parallel. If a handler fails,
        the error is logged but other handlers continue executing.

        Args:
            event: Domain event to publish
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug(f"📭 No handlers registered for {event_type.__name__}")
            return

        logger.info(f"📤 Publishing {event.event_name()} (id: {event.event_id}) " f"to {len(handlers)} handler(s)")

        # Execute handlers concurrently
        async with self._lock:
            tasks = [self._execute_handler(handler, event) for handler in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_handler(self, handler: EventHandler, event: DomainEvent) -> None:
        """Execute a single handler with error handling.

        Args:
            handler: Handler to execute
            event: Event to handle
        """
        try:
            await handler.handle(event)
            logger.info(f"✅ {handler.__class__.__name__} handled {event.event_name()}")
        except Exception as e:
            logger.error(
                f"❌ {handler.__class__.__name__} failed to handle " f"{event.event_name()}: {str(e)}",
                exc_info=True,
            )

    def clear(self) -> None:
        """Clear all registered handlers (useful for testing)."""
        self._handlers.clear()
        logger.info("🧹 Event bus cleared")
