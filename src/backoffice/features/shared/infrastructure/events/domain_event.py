"""Base domain event for event-driven architecture."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    Domain events represent something that happened in the domain that domain
    experts care about. Events are immutable and have occurred in the past.

    Attributes:
        event_id: Unique identifier for this event instance
        occurred_at: Timestamp when the event occurred
        aggregate_id: ID of the aggregate root that emitted this event
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str | None = None

    def event_name(self) -> str:
        """Get the event name (class name by default).

        Returns:
            Event name string
        """
        return self.__class__.__name__
