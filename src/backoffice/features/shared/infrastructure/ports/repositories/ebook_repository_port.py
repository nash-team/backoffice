from abc import ABC, abstractmethod

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.shared.domain.entities.pagination import PaginatedResult, PaginationParams


class EbookRepositoryPort(ABC):
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
    async def get_paginated(self, params: PaginationParams) -> PaginatedResult[Ebook]:
        """
        Récupère une page d'ebooks avec pagination.

        Args:
            params: Paramètres de pagination (page, size)

        Returns:
            PaginatedResult: Résultats paginés avec métadonnées
        """
        pass

    @abstractmethod
    async def get_paginated_by_status(
        self, status: EbookStatus, params: PaginationParams
    ) -> PaginatedResult[Ebook]:
        """
        Récupère une page d'ebooks filtrés par statut avec pagination.

        Args:
            status: Statut des ebooks à récupérer
            params: Paramètres de pagination (page, size)

        Returns:
            PaginatedResult: Résultats paginés avec métadonnées
        """
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
