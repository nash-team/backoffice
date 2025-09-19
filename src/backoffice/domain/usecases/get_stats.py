from dataclasses import dataclass

from backoffice.domain.entities.ebook import EbookStatus
from backoffice.infrastructure.ports.repositories.ebook_repository_port import (
    EbookRepositoryPort as EbookRepository,
)


@dataclass
class Stats:
    total_ebooks: int
    pending_ebooks: int
    validated_ebooks: int


class GetStatsUseCase:
    def __init__(self, ebook_repository: EbookRepository) -> None:
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
