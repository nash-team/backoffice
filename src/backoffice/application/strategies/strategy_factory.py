"""Factory for creating ebook generation strategies."""

import logging

from backoffice.application.strategies.coloring_book_strategy import ColoringBookStrategy
from backoffice.domain.cover_generation import CoverGenerationService
from backoffice.domain.entities.generation_request import EbookType
from backoffice.domain.page_generation import ContentPageGenerationService
from backoffice.domain.pdf_assembly import PDFAssemblyService
from backoffice.domain.ports.ebook_generation_strategy_port import EbookGenerationStrategyPort
from backoffice.infrastructure.providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


class StrategyFactory:
    """Factory for creating ebook generation strategies.

    Creates strategy with proper dependency injection using hexagonal architecture.
    """

    @staticmethod
    def create_strategy(
        ebook_type: EbookType, request_id: str | None = None
    ) -> EbookGenerationStrategyPort:
        """Create generation strategy for ebook type.

        Args:
            ebook_type: Type of ebook to generate
            request_id: Optional request ID for token tracking

        Returns:
            Strategy instance with injected dependencies

        Raises:
            ValueError: If ebook type not supported
        """
        logger.info(f"Creating strategy for ebook type: {ebook_type.value}")

        if ebook_type == EbookType.COLORING:
            return StrategyFactory._create_coloring_book_strategy(request_id)
        else:
            raise ValueError(f"Ebook type {ebook_type.value} not yet supported")

    @staticmethod
    def _create_coloring_book_strategy(request_id: str | None = None) -> ColoringBookStrategy:
        """Create coloring book strategy with dependencies.

        Args:
            request_id: Optional request ID for token tracking

        Returns:
            ColoringBookStrategy with injected services
        """
        # Note: TrackTokenUsageUseCase now created directly by providers via ProviderFactory
        # Create strategy with service injection (no more token_tracker)
        track_usage_usecase = None  # Providers will create it themselves if needed

        # Create providers via factory with usage tracking
        cover_provider = ProviderFactory.create_cover_provider(
            track_usage_usecase=track_usage_usecase,
            request_id=request_id,
        )
        pages_provider = ProviderFactory.create_content_page_provider(
            track_usage_usecase=track_usage_usecase,
            request_id=request_id,
        )
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

        # Create strategy with service injection (no more token_tracker)
        strategy = ColoringBookStrategy(
            cover_service=cover_service,
            pages_service=pages_service,
            assembly_service=assembly_service,
        )

        logger.info("✅ ColoringBookStrategy created with dependencies")
        return strategy
