"""Factory for creating LLM adapters based on configuration."""

import logging
import os

from backoffice.domain.ports.content_generation_port import ContentGenerationPort
from backoffice.domain.ports.image_generation_port import ImageGenerationPort

logger = logging.getLogger(__name__)


class LLMAdapterFactory:
    """Factory for creating appropriate LLM adapters based on configuration.

    Supports multiple providers:
    - openai: Direct OpenAI API
    - openrouter: OpenRouter (multi-model gateway)

    Usage:
        content_adapter = LLMAdapterFactory.create_content_adapter(
            model="anthropic/claude-3.5-sonnet"
        )
        image_adapter = LLMAdapterFactory.create_image_adapter(model="openai/dall-e-3")
    """

    @staticmethod
    def create_content_adapter(model: str | None = None) -> ContentGenerationPort:
        """Create content generation adapter based on configured provider.

        Args:
            model: Explicit model to use (e.g., "anthropic/claude-3.5-sonnet")
                   If None, uses LLM_TEXT_MODEL from environment

        Returns:
            ContentGenerationPort implementation

        Raises:
            ValueError: If provider is unknown or not configured
        """
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

        logger.info(f"Creating content adapter for provider: {provider}")

        if provider == "openrouter":
            from backoffice.infrastructure.adapters.openrouter_content_adapter import (
                OpenRouterContentAdapter,
            )

            adapter = OpenRouterContentAdapter(model=model)
            logger.info(
                f"Created OpenRouterContentAdapter with model: {adapter.openrouter_service.model}"
            )
            return adapter

        elif provider == "openai":
            from backoffice.infrastructure.adapters.openai_content_adapter import (
                OpenAIContentAdapter,
            )

            adapter = OpenAIContentAdapter()
            logger.info("Created OpenAIContentAdapter")
            return adapter

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Supported providers: openai, openrouter. "
                f"Please check LLM_PROVIDER environment variable."
            )

    @staticmethod
    def create_image_adapter(model: str | None = None) -> ImageGenerationPort:
        """Create image generation adapter based on model selection.

        Image generation options:
        1. Gemini via OpenRouter (uses LLM_API_KEY) - recommended
        2. DALL-E via OpenAI (uses OPENAI_API_KEY)

        Args:
            model: Explicit model to use. If None, uses LLM_IMAGE_MODEL from environment
                   - google/gemini-2.5-flash-image-preview: OpenRouter (recommended)
                   - dall-e-3, dall-e-2: OpenAI direct

        Returns:
            ImageGenerationPort implementation

        Raises:
            ValueError: If required API key is not configured
        """
        # Get the model to use (explicit or from env)
        selected_model = model or os.getenv(
            "LLM_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview"
        )
        logger.info(f"Creating image adapter for model: {selected_model}")

        # Check if it's a Gemini image model (use OpenRouter)
        if "gemini" in selected_model.lower() and "image" in selected_model.lower():
            provider = os.getenv("LLM_PROVIDER", "openrouter").lower()

            if provider == "openrouter":
                from backoffice.infrastructure.adapters.openrouter_image_adapter import (
                    OpenRouterImageAdapter,
                )

                adapter = OpenRouterImageAdapter(model=selected_model)
                logger.info(f"Created OpenRouterImageAdapter with model: {adapter.model}")
                return adapter
            else:
                raise ValueError(
                    f"Gemini image model requires LLM_PROVIDER=openrouter.\n"
                    f"Current provider: {provider}"
                )

        # Otherwise, use OpenAI directly for DALL-E
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.error("OPENAI_API_KEY not configured for DALL-E image generation")
            raise ValueError(
                "Configuration incomplète: OPENAI_API_KEY est manquante.\n\n"
                f"Le modèle {selected_model} nécessite une clé API OpenAI.\n\n"
                "Option recommandée: Utiliser Gemini via OpenRouter:\n"
                "  LLM_IMAGE_MODEL=google/gemini-2.5-flash-image-preview\n"
                "  LLM_API_KEY=your-openrouter-api-key\n\n"
                "Option alternative: Ajouter une clé OpenAI:\n"
                "  OPENAI_API_KEY=your-openai-api-key-here\n"
                "  LLM_IMAGE_MODEL=dall-e-3\n\n"
                "Obtenez une clé sur: https://platform.openai.com/api-keys"
            )

        from backoffice.infrastructure.adapters.openai_image_generator import (
            OpenAIImageGenerator,
        )

        adapter = OpenAIImageGenerator()
        logger.info(f"Created OpenAIImageGenerator for image generation (model: {selected_model})")
        return adapter

    @staticmethod
    def get_available_providers() -> list[str]:
        """Get list of available provider names.

        Returns:
            list: Available provider names
        """
        return ["openai", "openrouter"]

    @staticmethod
    def validate_provider_config() -> dict[str, bool]:
        """Validate current provider configuration.

        Returns:
            dict: Validation results with boolean flags
        """
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        results = {
            "provider_valid": provider in LLMAdapterFactory.get_available_providers(),
            "has_text_api_key": False,
            "has_image_api_key": False,
            "has_text_model": False,
            "has_image_model": False,
        }

        # Text generation validation (depends on provider)
        if provider == "openrouter":
            results["has_text_api_key"] = bool(os.getenv("LLM_API_KEY"))
            results["has_text_model"] = bool(os.getenv("LLM_TEXT_MODEL"))
        elif provider == "openai":
            results["has_text_api_key"] = bool(os.getenv("OPENAI_API_KEY"))
            results["has_text_model"] = True  # Uses hardcoded models

        # Image generation validation
        selected_model = os.getenv("LLM_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview")
        if "gemini" in selected_model.lower():
            results["has_image_api_key"] = bool(os.getenv("LLM_API_KEY"))
        else:
            results["has_image_api_key"] = bool(os.getenv("OPENAI_API_KEY"))
        results["has_image_model"] = bool(selected_model)

        return results
