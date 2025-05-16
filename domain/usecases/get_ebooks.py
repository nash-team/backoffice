from typing import List, Optional
from domain.entities.ebook import Ebook, EbookStatus
from domain.ports.ebook_repository import EbookRepository

class GetEbooksUseCase:
    def __init__(self, ebook_repository: EbookRepository):
        self.ebook_repository = ebook_repository

    async def execute(self, status: Optional[EbookStatus] = None) -> List[Ebook]:
        if status:
            return await self.ebook_repository.get_by_status(status)
        return await self.ebook_repository.get_all() 