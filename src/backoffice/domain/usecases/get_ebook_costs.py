"""Use case for retrieving ebook generation costs."""

import logging
from dataclasses import dataclass
from decimal import Decimal

from backoffice.domain.entities.ebook import Ebook
from backoffice.domain.ports.ebook.ebook_port import EbookPort

logger = logging.getLogger(__name__)


@dataclass
class EbookCostSummary:
    """Summary of ebook cost data."""

    ebook: Ebook
    cost: Decimal


class GetEbookCostsUseCase:
    """Use case for retrieving ebook generation costs.

    Returns list of ebooks with their generation costs for cost tracking and analysis.
    """

    def __init__(self, ebook_repository: EbookPort):
        """Initialize use case.

        Args:
            ebook_repository: Repository for ebook data access
        """
        self.ebook_repository = ebook_repository

    async def execute(self) -> list[EbookCostSummary]:
        """Execute use case to get ebook costs.

        Returns:
            List of EbookCostSummary with cost information
        """
        logger.info("📊 Fetching ebook costs")

        # Get all ebooks
        ebooks = await self.ebook_repository.get_all()

        # Build cost summaries
        summaries = []
        for ebook in ebooks:
            if ebook.generation_metadata is not None:
                summaries.append(
                    EbookCostSummary(
                        ebook=ebook,
                        cost=ebook.generation_metadata.cost,
                    )
                )

        # Sort by creation date descending (most recent first)
        summaries.sort(key=lambda x: x.ebook.created_at, reverse=True)

        logger.info(f"✅ Retrieved {len(summaries)} ebooks with cost data")
        return summaries
