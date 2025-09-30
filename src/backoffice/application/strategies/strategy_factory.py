"""Factory for creating ebook generation strategies."""

import logging

from backoffice.application.strategies.coloring_book_strategy import ColoringBookStrategy
from backoffice.domain.cover_generation import CoverGenerationService
from backoffice.domain.entities.generation_request import EbookType
from backoffice.domain.page_generation import ContentPageGenerationService
from backoffice.domain.pdf_assembly import PDFAssemblyService
from backoffice.infrastructure.providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


class StrategyFactory:
    """Factory for creating ebook generation strategies.

    Creates strategy with proper dependency injection using hexagonal architecture.
    """

    @staticmethod
    def create_strategy(ebook_type: EbookType) -> ColoringBookStrategy:
        """Create generation strategy for ebook type.

        Args:
            ebook_type: Type of ebook to generate

        Returns:
            Strategy instance with injected dependencies

        Raises:
            ValueError: If ebook type not supported
        """
        logger.info(f"Creating strategy for ebook type: {ebook_type.value}")

        if ebook_type == EbookType.COLORING:
            return StrategyFactory._create_coloring_book_strategy()
        else:
            raise ValueError(f"Ebook type {ebook_type.value} not yet supported")

    @staticmethod
    def _create_coloring_book_strategy() -> ColoringBookStrategy:
        """Create coloring book strategy with dependencies.

        Returns:
            ColoringBookStrategy with injected services
        """
        # Create providers via factory
        cover_provider = ProviderFactory.create_cover_provider()
        pages_provider = ProviderFactory.create_content_page_provider()
        assembly_provider = ProviderFactory.create_assembly_provider()

        # Create services with provider injection
        cover_service = CoverGenerationService(
            cover_port=cover_provider,
            enable_cache=True,
        )

        pages_service = ContentPageGenerationService(
            page_port=pages_provider,
            max_concurrent=3,  # V1: simple Semaphore limit
            enable_cache=True,
        )

        assembly_service = PDFAssemblyService(
            assembly_port=assembly_provider,
        )

        # Create strategy with service injection
        strategy = ColoringBookStrategy(
            cover_service=cover_service,
            pages_service=pages_service,
            assembly_service=assembly_service,
        )

        logger.info("✅ ColoringBookStrategy created with dependencies")
        return strategy
