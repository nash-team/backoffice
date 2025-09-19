"""
Cet adaptateur fournit une implémentation en mémoire du repository d'ebooks.
Il est principalement utilisé pour les tests et le développement.

L'implémentation stocke les ebooks dans une liste en mémoire et fournit
des méthodes CRUD basiques.
"""

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.infrastructure.ports.exceptions import DuplicateEntityError, EntityNotFoundError
from backoffice.infrastructure.ports.repositories.ebook_repository_port import EbookRepositoryPort


class InMemoryEbookRepository(EbookRepositoryPort):
    def __init__(self):
        self.ebooks: list[Ebook] = []

    async def create(self, ebook: Ebook) -> Ebook:
        """
        Crée un nouvel ebook en mémoire.

        Args:
            ebook: L'ebook à créer

        Returns:
            Ebook: L'ebook créé

        Raises:
            DuplicateEntityError: Si un ebook avec le même ID existe déjà
        """
        if await self.get_by_id(ebook.id):
            raise DuplicateEntityError(f"Un ebook avec l'ID {ebook.id} existe déjà")
        self.ebooks.append(ebook)
        return ebook

    async def get_by_id(self, id: int) -> Ebook | None:
        """
        Récupère un ebook par son ID.

        Args:
            id: L'ID de l'ebook à rechercher

        Returns:
            Optional[Ebook]: L'ebook trouvé ou None
        """
        return next((ebook for ebook in self.ebooks if ebook.id == id), None)

    async def update(self, ebook: Ebook) -> Ebook:
        """
        Met à jour un ebook existant.

        Args:
            ebook: L'ebook à mettre à jour

        Returns:
            Ebook: L'ebook mis à jour

        Raises:
            EntityNotFoundError: Si l'ebook n'existe pas
        """
        existing_ebook = await self.get_by_id(ebook.id)
        if not existing_ebook:
            raise EntityNotFoundError(f"L'ebook avec l'ID {ebook.id} n'existe pas")
        self.ebooks.remove(existing_ebook)
        self.ebooks.append(ebook)
        return ebook

    async def delete(self, id: int) -> None:
        """
        Supprime un ebook.

        Args:
            id: L'ID de l'ebook à supprimer

        Raises:
            EntityNotFoundError: Si l'ebook n'existe pas
        """
        ebook = await self.get_by_id(id)
        if not ebook:
            raise EntityNotFoundError(f"L'ebook avec l'ID {id} n'existe pas")
        self.ebooks.remove(ebook)

    async def list_all(self) -> list[Ebook]:
        """
        Liste tous les ebooks.

        Returns:
            List[Ebook]: La liste de tous les ebooks
        """
        return self.ebooks

    async def get_all(self) -> list[Ebook]:
        """
        Alias de list_all() pour maintenir la compatibilité avec l'interface existante.

        Returns:
            List[Ebook]: La liste de tous les ebooks
        """
        return await self.list_all()

    async def clear(self) -> None:
        """
        Vide le repository en mémoire.
        Utile pour les tests.
        """
        self.ebooks.clear()

    async def get_by_status(self, status: EbookStatus) -> list[Ebook]:
        """
        Récupère tous les ebooks avec un statut spécifique.

        Args:
            status: Le statut à rechercher

        Returns:
            List[Ebook]: La liste des ebooks avec le statut spécifié
        """
        return [ebook for ebook in self.ebooks if ebook.status == status]

    async def save(self, ebook: Ebook) -> Ebook:
        """
        Sauvegarde un ebook dans le repository.

        Args:
            ebook: L'ebook à sauvegarder

        Returns:
            Ebook: L'ebook sauvegardé
        """
        self.ebooks.append(ebook)
        return ebook
