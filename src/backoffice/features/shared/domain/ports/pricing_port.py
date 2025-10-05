"""Abstract port for model pricing.

This port defines the interface for fetching pricing information from various
AI model providers (OpenRouter, Anthropic, etc.). Implementations should handle
caching, retries, and provider-specific pricing structures.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Literal, TypedDict


class ModelPricing(TypedDict):
    """Pricing information for a model.

    Attributes:
        prompt_per_token: Cost per input token in USD (NOT per 1K tokens)
        completion_per_token: Cost per output token in USD (NOT per 1K tokens)
        per_request: Cost per request for image models
        unit: Billing unit type
        resolution_pricing: Optional pricing per resolution (e.g., {"1024x1024": 0.02})
        input_images_per_k: Cost per 1000 input images (for vision models)
        output_images_per_k: Cost per 1000 output images (for image generation)
    """

    prompt_per_token: Decimal
    completion_per_token: Decimal
    per_request: Decimal
    unit: Literal["per_token", "per_image"]
    resolution_pricing: dict[str, Decimal] | None
    input_images_per_k: Decimal | None
    output_images_per_k: Decimal | None


class PricingPort(ABC):
    """Abstract port for model pricing.

    Implementations: OpenRouter, Anthropic Direct, Custom API, etc.
    """

    @abstractmethod
    async def get_pricing(self) -> dict[str, ModelPricing]:
        """Get pricing table for all models.

        Returns:
            Dict mapping model_id -> pricing info
        """
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear pricing cache (force reload)."""
        pass
