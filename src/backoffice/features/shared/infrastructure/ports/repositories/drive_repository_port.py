"""
Ce port définit l'interface pour le repository Google Drive.
Il spécifie les contrats que doivent respecter toutes les implémentations
d'accès aux fichiers Google Drive.

Le port suit le principe d'inversion de dépendance en définissant une abstraction
que le domaine peut utiliser sans connaître les détails d'implémentation de l'API Google Drive.
"""

from abc import ABC, abstractmethod

from backoffice.features.shared.domain.entities.ebook import Ebook


class DriveRepositoryPort(ABC):
    @abstractmethod
    async def list_ebooks(self) -> list[Ebook]:
        """
        Liste tous les ebooks disponibles dans le Drive.

        Returns:
            List[Ebook]: La liste des ebooks trouvés

        Raises:
            DriveError: Si une erreur survient lors de l'accès au Drive
        """
        pass

    @abstractmethod
    async def get_ebook(self, _file_id: str) -> Ebook | None:
        """
        Récupère un ebook spécifique par son ID.

        Args:
            file_id: L'ID du fichier dans Google Drive

        Returns:
            Optional[Ebook]: L'ebook trouvé ou None

        Raises:
            DriveError: Si une erreur survient lors de l'accès au Drive
        """
        pass

    @abstractmethod
    async def update_ebook_status(self, _file_id: str, _status: str) -> None:
        """
        Met à jour le statut d'un ebook dans le Drive.

        Args:
            file_id: L'ID du fichier dans Google Drive
            status: Le nouveau statut à appliquer

        Raises:
            DriveError: Si une erreur survient lors de la mise à jour
        """
        pass

    @abstractmethod
    async def get_preview_url(self, _file_id: str) -> str:
        """
        Récupère l'URL de prévisualisation d'un ebook.

        Args:
            file_id: L'ID du fichier dans Google Drive

        Returns:
            str: L'URL de prévisualisation

        Raises:
            DriveError: Si une erreur survient lors de la récupération de l'URL
        """
        pass
