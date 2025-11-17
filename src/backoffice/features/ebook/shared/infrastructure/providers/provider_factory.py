"""Factory for creating provider instances (V1 slim)."""

import logging
import os

from backoffice.features.ebook.shared.domain.policies.model_registry import ModelRegistry
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssemblyPort
from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort

logger = logging.getLogger(__name__)


def _should_use_fakes() -> bool:
    """Check if we should use fake providers (E2E tests)."""
    return os.getenv("USE_FAKE_PROVIDERS", "false").lower() == "true"


class ProviderFactory:
    """Factory for creating provider instances based on model registry (V1 slim).

    V1 simplification:
    - Direct provider instantiation (no complex routing)
    - Uses ModelRegistry to determine which provider to use
    - Caches provider instances for performance
    """

    # Cache for provider instances (dict with key: provider+model)
    _cover_provider_cache: dict[str, CoverGenerationPort] = {}
    _page_provider_cache: dict[str, ContentPageGenerationPort] = {}
    _assembly_provider_cache: AssemblyPort | None = None

    @staticmethod
    def _make_cache_key(provider: str, model: str) -> str:
        """Create cache key from provider and model."""
        return f"{provider}:{model}"

    @staticmethod
    def clear_cache():
        """Clear all cached provider instances (useful for hot-reloading config changes)."""
        ProviderFactory._cover_provider_cache = {}
        ProviderFactory._page_provider_cache = {}
        ProviderFactory._assembly_provider_cache = None
        logger.info("🔄 Provider cache cleared")

    @staticmethod
    def create_cover_provider() -> CoverGenerationPort:
        """Create cover generation provider (real or fake).

        Uses caching for performance.

        Returns:
            CoverGenerationPort implementation (cached instance)

        Raises:
            ValueError: If provider not found or not configured
        """
        # Get model configuration
        registry = ModelRegistry.get_instance()
        model_mapping = registry.get_cover_model()

        # Create cache key
        cache_key = ProviderFactory._make_cache_key(
            model_mapping.provider,
            model_mapping.model,
        )

        # Return cached instance if available
        if cache_key in ProviderFactory._cover_provider_cache:
            logger.debug(f"♻️ Reusing cached cover provider: {cache_key}")
            return ProviderFactory._cover_provider_cache[cache_key]

        # Create new instance
        logger.info(f"Creating cover provider: {model_mapping.provider} / {model_mapping.model}")

        provider: CoverGenerationPort
        if model_mapping.provider == "openrouter":
            from backoffice.features.ebook.shared.infrastructure.providers.images.openrouter import (
                openrouter_image_provider as orp,
            )

            provider = orp.OpenRouterImageProvider(model=model_mapping.model)

        elif model_mapping.provider == "comfy":
            from backoffice.features.ebook.shared.infrastructure.providers.images.comfy import comfy_provider

            ComfyProvider = comfy_provider.ComfyProvider

            provider = ComfyProvider(model=model_mapping.model)

        elif model_mapping.provider == "gemini":
            from backoffice.features.ebook.shared.infrastructure.providers.images.gemini import (
                gemini_image_provider,
            )

            GeminiImageProvider = gemini_image_provider.GeminiImageProvider

            provider = GeminiImageProvider(model=model_mapping.model)

        else:
            raise ValueError(f"Unknown cover provider: {model_mapping.provider}. " f"Supported: openrouter, gemini")

        # Cache and return
        ProviderFactory._cover_provider_cache[cache_key] = provider
        return provider

    @staticmethod
    def create_content_page_provider() -> ContentPageGenerationPort:
        """Create content page generation provider (real or fake).

        Uses caching for performance.

        Returns:
            ContentPageGenerationPort implementation (cached instance)

        Raises:
            ValueError: If provider not found or not configured
        """
        # Get model configuration
        registry = ModelRegistry.get_instance()
        model_mapping = registry.get_page_model()

        # Create cache key
        cache_key = ProviderFactory._make_cache_key(
            model_mapping.provider,
            model_mapping.model,
        )

        # Return cached instance if available
        if cache_key in ProviderFactory._page_provider_cache:
            logger.debug(f"♻️ Reusing cached page provider: {cache_key}")
            return ProviderFactory._page_provider_cache[cache_key]

        # Create new instance
        logger.info(f"Creating content page provider: {model_mapping.provider} / {model_mapping.model}")

        provider: ContentPageGenerationPort
        if model_mapping.provider == "openrouter":
            from backoffice.features.ebook.shared.infrastructure.providers.images.openrouter import (
                openrouter_image_provider as orp,
            )

            provider = orp.OpenRouterImageProvider(model=model_mapping.model)

        elif model_mapping.provider == "comfy":
            from backoffice.features.ebook.shared.infrastructure.providers.images.comfy import comfy_provider

            ComfyProvider = comfy_provider.ComfyProvider

            provider = ComfyProvider(model=model_mapping.model)

        elif model_mapping.provider == "gemini":
            from backoffice.features.ebook.shared.infrastructure.providers.images.gemini import (
                gemini_image_provider,
            )

            GeminiImageProvider = gemini_image_provider.GeminiImageProvider

            provider = GeminiImageProvider(model=model_mapping.model)

        else:
            raise ValueError(f"Unknown content page provider: {model_mapping.provider}. " f"Supported: openrouter, gemini")

        # Cache and return
        ProviderFactory._page_provider_cache[cache_key] = provider
        return provider

    @staticmethod
    def create_assembly_provider() -> AssemblyPort:
        """Create PDF assembly provider.

        Uses caching for performance.

        Returns:
            AssemblyPort implementation (WeasyPrint, cached instance)
        """
        # Return cached instance if available
        if ProviderFactory._assembly_provider_cache is not None:
            logger.debug("♻️ Reusing cached assembly provider instance")
            return ProviderFactory._assembly_provider_cache

        from backoffice.features.ebook.shared.infrastructure.providers import (
            weasyprint_assembly_provider,
        )

        WeasyPrintAssemblyProvider = weasyprint_assembly_provider.WeasyPrintAssemblyProvider

        logger.info("Creating assembly provider: WeasyPrint")
        provider = WeasyPrintAssemblyProvider()

        # Cache and return
        ProviderFactory._assembly_provider_cache = provider
        return provider
