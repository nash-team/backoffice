"""Factory for creating LLM adapters based on configuration."""

import logging
import os

from backoffice.domain.ports.content_generation_port import ContentGenerationPort
from backoffice.domain.ports.image_generation_port import ImageGenerationPort

logger = logging.getLogger(__name__)


class LLMAdapterFactory:
    """Factory for creating LLM adapters using OpenRouter.

    All adapters use OpenRouter as the provider.

    Usage:
        content_adapter = LLMAdapterFactory.create_content_adapter(
            model="anthropic/claude-3.5-sonnet"
        )
        image_adapter = LLMAdapterFactory.create_image_adapter(
            model="google/gemini-2.5-flash-image-preview"
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

    @staticmethod
    def create_image_adapter(model: str | None = None) -> ImageGenerationPort:
        """Create image generation adapter (OpenRouter Gemini only).

        Args:
            model: Explicit model to use. If None, uses LLM_IMAGE_MODEL from environment
                   Default: google/gemini-2.5-flash-image-preview

        Returns:
            ImageGenerationPort implementation (OpenRouterImageAdapter)

        Raises:
            ValueError: If configuration is missing
        """
        from backoffice.infrastructure.adapters.openrouter_image_adapter import (
            OpenRouterImageAdapter,
        )

        selected_model = model or os.getenv(
            "LLM_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview"
        )

        adapter = OpenRouterImageAdapter(model=selected_model)
        logger.info(f"Created OpenRouterImageAdapter with model: {adapter.model}")
        return adapter
