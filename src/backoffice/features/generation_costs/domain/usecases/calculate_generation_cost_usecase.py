"""Use case for calculating total generation cost."""

import logging

from backoffice.features.generation_costs.domain.events.cost_calculated_event import (
    CostCalculatedEvent,
)
from backoffice.features.generation_costs.domain.ports.token_tracker_port import TokenTrackerPort
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class CalculateGenerationCostUseCase:
    """Use case for calculating total generation cost.

    Retrieves all usage records for a request, calculates totals,
    and emits a CostCalculatedEvent.
    """

    def __init__(self, token_tracker: TokenTrackerPort, event_bus: EventBus):
        """Initialize use case.

        Args:
            token_tracker: Port for retrieving usage data
            event_bus: Event bus for publishing events
        """
        self.token_tracker = token_tracker
        self.event_bus = event_bus

    async def execute(self, request_id: str, ebook_id: int | None = None) -> None:
        """Calculate total cost for a generation request.

        Args:
            request_id: Generation request ID
            ebook_id: ID of generated ebook (optional)
        """
        logger.info(f"💰 Calculating total cost for request {request_id}")

        # Get cost calculation with all usage records
        calculation = await self.token_tracker.get_cost_calculation(request_id)

        # Emit cost calculated event
        event = CostCalculatedEvent(
            request_id=request_id,
            ebook_id=ebook_id,
            total_cost=calculation.total_cost,
            total_tokens=calculation.total_tokens,
            api_call_count=calculation.api_call_count,
        )
        await self.event_bus.publish(event)

        logger.info(
            f"✅ Cost calculated for request {request_id}: "
            f"${calculation.total_cost} ({calculation.api_call_count} API calls)"
        )
