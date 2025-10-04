"""Factory for creating LLM adapters based on configuration."""

import logging

from backoffice.domain.ports.content_generation_port import ContentGenerationPort

logger = logging.getLogger(__name__)


class LLMAdapterFactory:
    """Factory for creating LLM adapters using OpenRouter.

    All adapters use OpenRouter as the provider.

    Usage:
        content_adapter = LLMAdapterFactory.create_content_adapter(
            model="anthropic/claude-3.5-sonnet"
        )
    """

    @staticmethod
    def create_content_adapter(model: str | None = None) -> ContentGenerationPort:
        """Create content generation adapter (OpenRouter only).

        Args:
            model: Explicit model to use (e.g., "anthropic/claude-3.5-sonnet")
                   If None, uses LLM_TEXT_MODEL from environment

        Returns:
            ContentGenerationPort implementation (OpenRouter)

        Raises:
            ValueError: If configuration is missing
        """
        from backoffice.infrastructure.adapters.openrouter_content_adapter import (
            OpenRouterContentAdapter,
        )

        adapter = OpenRouterContentAdapter(model=model)
        logger.info(
            f"Created OpenRouterContentAdapter with model: {adapter.openrouter_service.model}"
        )
        return adapter
