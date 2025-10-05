"""Port for token usage tracking and persistence."""

from abc import ABC, abstractmethod

from backoffice.features.generation_costs.domain.entities.cost_calculation import CostCalculation
from backoffice.features.generation_costs.domain.entities.token_usage import ImageUsage, TokenUsage


class TokenTrackerPort(ABC):
    """Port for tracking and persisting token usage data.

    This port abstracts the persistence of token and image usage records
    for cost tracking purposes.
    """

    @abstractmethod
    async def save_token_usage(self, request_id: str, usage: TokenUsage) -> None:
        """Save a token usage record.

        Args:
            request_id: Generation request ID
            usage: Token usage data to persist
        """
        pass

    @abstractmethod
    async def save_image_usage(self, request_id: str, usage: ImageUsage) -> None:
        """Save an image usage record.

        Args:
            request_id: Generation request ID
            usage: Image usage data to persist
        """
        pass

    @abstractmethod
    async def get_cost_calculation(self, request_id: str) -> CostCalculation:
        """Retrieve cost calculation for a generation request.

        Args:
            request_id: Generation request ID

        Returns:
            CostCalculation with all usage records and totals
        """
        pass

    @abstractmethod
    async def get_all_cost_calculations(self) -> list[CostCalculation]:
        """Retrieve all cost calculations.

        Returns:
            List of all cost calculations, sorted by creation date descending
        """
        pass
