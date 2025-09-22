from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.entities.pagination import PaginatedResult, PaginationParams
from backoffice.infrastructure.ports.repositories.ebook_repository_port import (
    EbookRepositoryPort as EbookRepository,
)


class GetEbooksUseCase:
    def __init__(self, ebook_repository: EbookRepository) -> None:
        self.ebook_repository = ebook_repository

    async def execute(self, status: EbookStatus | None = None) -> list[Ebook]:
        if status:
            return await self.ebook_repository.get_by_status(status)
        return await self.ebook_repository.get_all()

    async def execute_paginated(
        self, params: PaginationParams, status: EbookStatus | None = None
    ) -> PaginatedResult[Ebook]:
        """Execute with pagination support"""
        if status:
            return await self.ebook_repository.get_paginated_by_status(status, params)
        return await self.ebook_repository.get_paginated(params)
