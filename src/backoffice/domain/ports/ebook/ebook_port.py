from abc import ABC, abstractmethod

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.entities.pagination import PaginatedResult, PaginationParams


class EbookPort(ABC):
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

    @abstractmethod
    async def save(self, ebook: Ebook) -> Ebook:
        """
        Sauvegarde un ebook (create ou update selon qu'il existe déjà).

        Args:
            ebook: L'ebook à sauvegarder

        Returns:
            Ebook: L'ebook sauvegardé
        """
        pass

    @abstractmethod
    async def get_paginated(self, params: PaginationParams) -> PaginatedResult[Ebook]:
        """
        Récupère une page d'ebooks avec pagination.

        Args:
            params: Paramètres de pagination

        Returns:
            PaginatedResult[Ebook]: Résultat paginé
        """
        pass

    @abstractmethod
    async def get_paginated_by_status(
        self, status: EbookStatus, params: PaginationParams
    ) -> PaginatedResult[Ebook]:
        """
        Récupère une page d'ebooks filtrés par statut avec pagination.

        Args:
            status: Statut à filtrer
            params: Paramètres de pagination

        Returns:
            PaginatedResult[Ebook]: Résultat paginé filtré
        """
        pass
