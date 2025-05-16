from typing import List, Optional
from domain.entities.ebook import Ebook, EbookStatus
from domain.ports.ebook_repository import EbookRepository

class InMemoryEbookRepository(EbookRepository):
    def __init__(self):
        self.ebooks: List[Ebook] = []

    async def get_all(self) -> List[Ebook]:
        return self.ebooks

    async def get_by_id(self, ebook_id: int) -> Optional[Ebook]:
        return next((ebook for ebook in self.ebooks if ebook.id == ebook_id), None)

    async def get_by_status(self, status: EbookStatus) -> List[Ebook]:
        return [ebook for ebook in self.ebooks if ebook.status == status]

    async def save(self, ebook: Ebook) -> Ebook:
        existing_ebook = await self.get_by_id(ebook.id)
        if existing_ebook:
            self.ebooks.remove(existing_ebook)
        self.ebooks.append(ebook)
        return ebook 