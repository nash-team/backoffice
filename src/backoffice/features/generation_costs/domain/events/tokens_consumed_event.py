"""Event emitted when tokens are consumed during generation."""

from dataclasses import dataclass
from decimal import Decimal

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class TokensConsumedEvent(DomainEvent):
    """Event emitted when an API call consumes tokens.

    This event is emitted by the infrastructure layer (e.g., OpenRouterImageProvider)
    after each successful API call that consumes tokens.

    Attributes:
        request_id: Unique ID for the generation request
        model: Model ID used for the API call
        prompt_tokens: Number of input tokens consumed
        completion_tokens: Number of output tokens generated
        cost: Calculated cost for this API call in USD
    """

    request_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: Decimal

    def __post_init__(self):
        """Set aggregate_id to request_id after frozen initialization."""
        # Use object.__setattr__ for frozen dataclass
        if self.aggregate_id is None:
            object.__setattr__(self, "aggregate_id", self.request_id)
