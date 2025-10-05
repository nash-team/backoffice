"""Event emitted when total generation cost is calculated."""

from dataclasses import dataclass
from decimal import Decimal

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CostCalculatedEvent(DomainEvent):
    """Event emitted when total cost for a generation request is calculated.

    This event is emitted after all API calls for a generation request are
    complete and the total cost has been calculated.

    Attributes:
        request_id: Unique ID for the generation request
        ebook_id: ID of the generated ebook (if applicable)
        total_cost: Total cost for all API calls in USD
        total_tokens: Total tokens consumed (prompt + completion)
        api_call_count: Number of API calls made
    """

    request_id: str
    ebook_id: int | None
    total_cost: Decimal
    total_tokens: int
    api_call_count: int

    def __post_init__(self):
        """Set aggregate_id to request_id after frozen initialization."""
        object.__setattr__(self, "aggregate_id", self.request_id)
