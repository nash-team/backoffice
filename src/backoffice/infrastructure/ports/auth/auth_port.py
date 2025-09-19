"""
Ce port définit l'interface pour l'authentification des utilisateurs.
Il spécifie les contrats que doivent respecter toutes les implémentations d'authentification
(comme JWT, OAuth2, etc.).

Le port suit le principe d'inversion de dépendance en définissant une abstraction
que le domaine peut utiliser sans connaître les détails d'implémentation.
"""

from abc import ABC, abstractmethod

from backoffice.domain.entities.user import User


class AuthPort(ABC):
    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> User | None:
        """
        Authentifie un utilisateur avec son email et son mot de passe.

        Args:
            email: L'email de l'utilisateur
            password: Le mot de passe en clair

        Returns:
            User | None: L'utilisateur authentifié ou None si l'authentification échoue
        """
        pass

    @abstractmethod
    async def create_access_token(self, data: dict) -> str:
        """
        Crée un token d'accès pour un utilisateur authentifié.

        Args:
            data: Les données à encoder dans le token (typiquement l'ID ou l'email de l'utilisateur)

        Returns:
            str: Le token d'accès généré
        """
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> dict:
        """
        Vérifie la validité d'un token d'accès.

        Args:
            token: Le token à vérifier

        Returns:
            dict: Les données décodées du token

        Raises:
            InvalidTokenError: Si le token est invalide ou expiré
        """
        pass
