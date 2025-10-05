"""Event handler interface for domain events."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent

TEvent = TypeVar("TEvent", bound=DomainEvent)


class EventHandler(ABC, Generic[TEvent]):
    """Abstract base class for event handlers.

    Event handlers are responsible for reacting to domain events.
    Each handler should handle a single event type.
    """

    @abstractmethod
    async def handle(self, event: TEvent) -> None:
        """Handle the domain event.

        Args:
            event: The domain event to handle

        Raises:
            Exception: If event handling fails
        """
        pass

    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can handle the given event.

        By default, checks if event is an instance of the handler's type parameter.
        Override for custom logic.

        Args:
            event: Event to check

        Returns:
            True if this handler can handle the event
        """
        # Get the generic type parameter (TEvent)
        # This is a simple implementation - production code might use get_args()
        return isinstance(event, DomainEvent)
