"""Factory for creating provider instances (V1 slim)."""

import logging

from backoffice.domain.policies.model_registry import ModelRegistry
from backoffice.domain.ports.assembly_port import AssemblyPort
from backoffice.domain.ports.content_page_generation_port import ContentPageGenerationPort
from backoffice.domain.ports.cover_generation_port import CoverGenerationPort

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating provider instances based on model registry (V1 slim).

    V1 simplification:
    - Direct provider instantiation (no complex routing)
    - Uses ModelRegistry to determine which provider to use
    """

    @staticmethod
    def create_cover_provider() -> CoverGenerationPort:
        """Create cover generation provider.

        Returns:
            CoverGenerationPort implementation

        Raises:
            ValueError: If provider not found or not configured
        """
        registry = ModelRegistry.get_instance()
        model_mapping = registry.get_cover_model()

        logger.info(f"Creating cover provider: {model_mapping.provider} / {model_mapping.model}")

        if model_mapping.provider == "openrouter":
            from backoffice.infrastructure.providers.openrouter_cover_provider import (
                OpenRouterCoverProvider,
            )

            return OpenRouterCoverProvider(model=model_mapping.model)

        else:
            raise ValueError(
                f"Unknown cover provider: {model_mapping.provider}. " f"Supported: openrouter"
            )

    @staticmethod
    def create_content_page_provider() -> ContentPageGenerationPort:
        """Create content page generation provider.

        Returns:
            ContentPageGenerationPort implementation

        Raises:
            ValueError: If provider not found or not configured
        """
        registry = ModelRegistry.get_instance()
        model_mapping = registry.get_page_model()

        logger.info(
            f"Creating content page provider: {model_mapping.provider} / {model_mapping.model}"
        )

        if model_mapping.provider == "openrouter":
            from backoffice.infrastructure.providers.openrouter_cover_provider import (
                OpenRouterCoverProvider,
            )

            return OpenRouterCoverProvider(model=model_mapping.model)

        else:
            raise ValueError(
                f"Unknown content page provider: {model_mapping.provider}. "
                f"Supported: openrouter"
            )

    @staticmethod
    def create_assembly_provider() -> AssemblyPort:
        """Create PDF assembly provider.

        Returns:
            AssemblyPort implementation (WeasyPrint)
        """
        from backoffice.infrastructure.providers.weasyprint_assembly_provider import (
            WeasyPrintAssemblyProvider,
        )

        logger.info("Creating assembly provider: WeasyPrint")
        return WeasyPrintAssemblyProvider()
