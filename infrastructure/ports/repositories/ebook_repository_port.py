from abc import ABC, abstractmethod

from domain.entities.ebook import Ebook


class EbookRepositoryPort(ABC):
    @abstractmethod
    async def get_all(self) -> list[Ebook]:
        pass

    @abstractmethod
    async def get_by_id(self, id: int) -> Ebook:
        pass
