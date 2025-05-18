from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.ebook import Ebook, EbookStatus


class EbookRepository(ABC):
    @abstractmethod
    async def get_all(self) -> List[Ebook]:
        pass

    @abstractmethod
    async def get_by_id(self, ebook_id: int) -> Optional[Ebook]:
        pass

    @abstractmethod
    async def get_by_status(self, status: EbookStatus) -> List[Ebook]:
        pass

    @abstractmethod
    async def save(self, ebook: Ebook) -> Ebook:
        pass
