"""Cost calculation value object for aggregating generation costs."""

from dataclasses import dataclass, field
from decimal import Decimal

from backoffice.features.generation_costs.domain.entities.token_usage import ImageUsage, TokenUsage


@dataclass
class CostCalculation:
    """Value object for aggregating costs across multiple API calls.

    Aggregates token and image usage costs for a complete ebook generation
    request. Provides methods for calculating totals and averages.

    Attributes:
        request_id: Unique identifier for the generation request
        token_usages: List of token-based API calls
        image_usages: List of image-based API calls
    """

    request_id: str
    token_usages: list[TokenUsage] = field(default_factory=list)
    image_usages: list[ImageUsage] = field(default_factory=list)

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost across all API calls.

        Returns:
            Total cost in USD (Decimal for precision)
        """
        token_cost = sum((u.cost for u in self.token_usages), Decimal("0"))
        image_cost = sum((u.cost for u in self.image_usages), Decimal("0"))
        return token_cost + image_cost

    @property
    def total_prompt_tokens(self) -> int:
        """Calculate total prompt tokens across all token-based calls.

        Returns:
            Total prompt tokens
        """
        return sum(u.prompt_tokens for u in self.token_usages)

    @property
    def total_completion_tokens(self) -> int:
        """Calculate total completion tokens across all token-based calls.

        Returns:
            Total completion tokens
        """
        return sum(u.completion_tokens for u in self.token_usages)

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens (prompt + completion).

        Returns:
            Total tokens
        """
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def total_input_images(self) -> int:
        """Calculate total input images across all image-based calls.

        Returns:
            Total input images
        """
        return sum(u.input_images for u in self.image_usages)

    @property
    def total_output_images(self) -> int:
        """Calculate total output images across all image-based calls.

        Returns:
            Total output images
        """
        return sum(u.output_images for u in self.image_usages)

    @property
    def api_call_count(self) -> int:
        """Calculate total number of API calls.

        Returns:
            Total API calls (token + image)
        """
        return len(self.token_usages) + len(self.image_usages)

    @property
    def average_cost_per_call(self) -> Decimal:
        """Calculate average cost per API call.

        Returns:
            Average cost per call, or Decimal("0") if no calls
        """
        if self.api_call_count == 0:
            return Decimal("0")
        return self.total_cost / Decimal(str(self.api_call_count))
