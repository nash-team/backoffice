from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.entities.pagination import PaginatedResult, PaginationParams
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort


class GetEbooksUseCase:
    def __init__(self, ebook_repository: EbookPort) -> None:
        self.ebook_repository = ebook_repository

    async def execute(self, status: EbookStatus | None = None) -> list[Ebook]:
        if status:
            return await self.ebook_repository.get_by_status(status)
        return await self.ebook_repository.get_all()

    async def execute_paginated(self, params: PaginationParams, status: EbookStatus | None = None) -> PaginatedResult[Ebook]:
        """Execute with pagination support"""
        if status:
            return await self.ebook_repository.get_paginated_by_status(status, params)
        return await self.ebook_repository.get_paginated(params)
