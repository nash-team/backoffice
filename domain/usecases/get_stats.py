from dataclasses import dataclass

from domain.entities.ebook import EbookStatus
from domain.ports.ebook.ebook_port import EbookRepository


@dataclass
class Stats:
    total_ebooks: int
    pending_ebooks: int
    validated_ebooks: int


class GetStatsUseCase:
    def __init__(self, ebook_repository: EbookRepository):
        self.ebook_repository = ebook_repository

    async def execute(self) -> Stats:
        all_ebooks = await self.ebook_repository.get_all()
        pending_ebooks = await self.ebook_repository.get_by_status(EbookStatus.PENDING)
        validated_ebooks = await self.ebook_repository.get_by_status(EbookStatus.VALIDATED)

        return Stats(
            total_ebooks=len(all_ebooks),
            pending_ebooks=len(pending_ebooks),
            validated_ebooks=len(validated_ebooks),
        )
