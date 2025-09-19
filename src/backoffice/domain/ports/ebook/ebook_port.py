from abc import ABC, abstractmethod

from backoffice.domain.entities.ebook import Ebook, EbookStatus


class EbookRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[Ebook]:
        pass

    @abstractmethod
    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        pass

    @abstractmethod
    async def get_by_status(self, status: EbookStatus) -> list[Ebook]:
        pass

    @abstractmethod
    async def create(self, ebook: Ebook) -> Ebook:
        """
        Crée un nouvel ebook.

        Args:
            ebook: L'ebook à créer

        Returns:
            Ebook: L'ebook créé avec son ID et sa date de création
        """
        pass

    @abstractmethod
    async def update(self, ebook: Ebook) -> Ebook:
        """
        Met à jour un ebook existant (notamment le statut).

        Args:
            ebook: L'ebook à mettre à jour

        Returns:
            Ebook: L'ebook mis à jour

        Raises:
            EbookNotFoundError: Si l'ebook n'existe pas
        """
        pass
