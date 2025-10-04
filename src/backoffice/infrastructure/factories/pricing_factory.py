"""Factory to create pricing adapter based on configuration.

This factory enables easy switching between pricing providers (OpenRouter, Anthropic, etc.)
via environment configuration, following the hexagonal architecture pattern.
"""

import logging
import os

from backoffice.domain.ports.pricing_port import PricingPort
from backoffice.infrastructure.adapters.openrouter_pricing_adapter import (
    OpenRouterPricingAdapter,
)

logger = logging.getLogger(__name__)


class PricingFactory:
    """Factory to create pricing adapter based on environment configuration."""

    _instance: PricingPort | None = None  # Singleton pattern

    @classmethod
    def create_pricing_adapter(cls) -> PricingPort:
        """Create pricing adapter (singleton).

        Returns:
            PricingPort implementation based on PRICING_PROVIDER env var
        """
        if cls._instance is None:
            provider = os.getenv("PRICING_PROVIDER", "openrouter").lower()

            if provider == "openrouter":
                logger.info("🔧 Using OpenRouter pricing adapter")
                cls._instance = OpenRouterPricingAdapter()
            else:
                logger.warning(f"⚠️ Unknown pricing provider: {provider}, defaulting to OpenRouter")
                cls._instance = OpenRouterPricingAdapter()

        return cls._instance
