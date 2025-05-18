"""
Ce port définit l'interface pour le repository des utilisateurs.
Il spécifie les contrats que doivent respecter toutes les implémentations
de stockage des utilisateurs (base de données, mémoire, etc.).

Le port suit le principe d'inversion de dépendance en définissant une abstraction
que le domaine peut utiliser sans connaître les détails d'implémentation du stockage.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.user import User


class UserRepositoryPort(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Crée un nouvel utilisateur.

        Args:
            user: L'utilisateur à créer

        Returns:
            User: L'utilisateur créé avec son ID

        Raises:
            DuplicateUserError: Si un utilisateur avec le même email existe déjà
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Récupère un utilisateur par son email.

        Args:
            email: L'email de l'utilisateur à rechercher

        Returns:
            Optional[User]: L'utilisateur trouvé ou None
        """
        pass

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[User]:
        """
        Récupère un utilisateur par son ID.

        Args:
            id: L'ID de l'utilisateur à rechercher

        Returns:
            Optional[User]: L'utilisateur trouvé ou None
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """
        Met à jour un utilisateur existant.

        Args:
            user: L'utilisateur à mettre à jour

        Returns:
            User: L'utilisateur mis à jour

        Raises:
            UserNotFoundError: Si l'utilisateur n'existe pas
        """
        pass

    @abstractmethod
    async def delete(self, id: int) -> None:
        """
        Supprime un utilisateur.

        Args:
            id: L'ID de l'utilisateur à supprimer

        Raises:
            UserNotFoundError: Si l'utilisateur n'existe pas
        """
        pass

    @abstractmethod
    async def list_all(self) -> List[User]:
        """
        Liste tous les utilisateurs.

        Returns:
            List[User]: La liste de tous les utilisateurs
        """
        pass
