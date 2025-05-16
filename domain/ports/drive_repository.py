from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.ebook import Ebook

class DriveRepository(ABC):
    @abstractmethod
    async def list_ebooks(self) -> List[Ebook]:
        """Récupère la liste des ebooks depuis le Drive"""
        pass

    @abstractmethod
    async def get_ebook(self, file_id: str) -> Optional[Ebook]:
        """Récupère un ebook spécifique depuis le Drive"""
        pass

    @abstractmethod
    async def update_ebook_status(self, file_id: str, status: str) -> None:
        """Met à jour le statut d'un ebook dans le Drive"""
        pass 