"""Use case for retrieving ebook lifecycle statistics."""

from dataclasses import dataclass

from backoffice.features.shared.domain.entities.ebook import EbookStatus
from backoffice.features.shared.domain.ports.ebook.ebook_port import EbookPort


@dataclass
class Stats:
    """Statistics about ebook lifecycle states.

    Attributes:
        total_ebooks: Total number of ebooks
        draft_ebooks: Number of ebooks in DRAFT status
        approved_ebooks: Number of ebooks in APPROVED status
        rejected_ebooks: Number of ebooks in REJECTED status
    """

    total_ebooks: int
    draft_ebooks: int
    approved_ebooks: int
    rejected_ebooks: int


class GetStatsUseCase:
    """Use case for retrieving ebook lifecycle statistics.

    This use case aggregates ebook counts by status for dashboard display.
    """

    def __init__(self, ebook_repository: EbookPort) -> None:
        """Initialize use case with dependencies.

        Args:
            ebook_repository: Repository for ebook queries
        """
        self.ebook_repository = ebook_repository

    async def execute(self) -> Stats:
        """Retrieve ebook statistics.

        Returns:
            Stats object with counts by status
        """
        all_ebooks = await self.ebook_repository.get_all()
        draft_ebooks = await self.ebook_repository.get_by_status(EbookStatus.DRAFT)
        approved_ebooks = await self.ebook_repository.get_by_status(EbookStatus.APPROVED)
        rejected_ebooks = await self.ebook_repository.get_by_status(EbookStatus.REJECTED)

        return Stats(
            total_ebooks=len(all_ebooks),
            draft_ebooks=len(draft_ebooks),
            approved_ebooks=len(approved_ebooks),
            rejected_ebooks=len(rejected_ebooks),
        )
