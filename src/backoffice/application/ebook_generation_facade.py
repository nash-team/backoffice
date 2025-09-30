"""Facade for ebook generation using hexagonal architecture."""

import logging
import uuid

from backoffice.application.strategies.strategy_factory import StrategyFactory
from backoffice.domain.entities.generation_request import (
    AgeGroup,
    EbookType,
    GenerationRequest,
    GenerationResult,
)

logger = logging.getLogger(__name__)


class EbookGenerationFacade:
    """Facade for ebook generation using hexagonal architecture.

    This facade provides a simple interface for ebook generation and handles:
    - Request ID generation
    - Strategy creation and execution
    - Error handling and logging
    """

    @staticmethod
    async def generate_coloring_book(
        title: str,
        theme: str,
        age_group: AgeGroup,
        page_count: int,
        seed: int | None = None,
    ) -> GenerationResult:
        """Generate a coloring book.

        Args:
            title: Book title
            theme: Theme description
            age_group: Target age group
            page_count: Number of content pages
            seed: Random seed for reproducibility

        Returns:
            GenerationResult with PDF URI and metadata

        Raises:
            DomainError: If generation fails
        """
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Create generation request
        request = GenerationRequest(
            title=title,
            theme=theme,
            age_group=age_group,
            ebook_type=EbookType.COLORING,
            page_count=page_count,
            request_id=request_id,
            seed=seed,
        )

        logger.info(f"🎨 Generating coloring book: {request_id}")

        # Create strategy and generate
        strategy = StrategyFactory.create_strategy(EbookType.COLORING)
        result = await strategy.generate(request)

        logger.info(f"✅ Coloring book generated: {result.pdf_uri}")
        return result
