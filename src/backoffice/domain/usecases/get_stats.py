from dataclasses import dataclass

from backoffice.domain.entities.ebook import EbookStatus
from backoffice.domain.ports.ebook.ebook_port import EbookPort


@dataclass
class Stats:
    total_ebooks: int
    draft_ebooks: int
    approved_ebooks: int
    rejected_ebooks: int


class GetStatsUseCase:
    def __init__(self, ebook_repository: EbookPort) -> None:
        self.ebook_repository = ebook_repository

    async def execute(self) -> Stats:
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
