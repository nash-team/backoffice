from abc import ABC, abstractmethod

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.entities.pagination import PaginatedResult, PaginationParams


class EbookQueryPort(ABC):
    """Port for ebook query operations with pagination support"""

    @abstractmethod
    async def list_paginated(self, params: PaginationParams) -> PaginatedResult[Ebook]:
        """
        List ebooks with pagination.

        Args:
            params: Pagination parameters

        Returns:
            PaginatedResult containing ebooks and pagination metadata
        """
        pass

    @abstractmethod
    async def list_paginated_by_status(
        self, status: EbookStatus, params: PaginationParams
    ) -> PaginatedResult[Ebook]:
        """
        List ebooks filtered by status with pagination.

        Args:
            status: Ebook status filter
            params: Pagination parameters

        Returns:
            PaginatedResult containing filtered ebooks and pagination metadata
        """
        pass
