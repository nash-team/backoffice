"""
Ce port définit l'interface pour l'authentification avec Google.
Il spécifie les contrats que doivent respecter toutes les implémentations
d'authentification Google (OAuth2, Service Account, etc.).

Le port suit le principe d'inversion de dépendance en définissant une abstraction
que le domaine peut utiliser sans connaître les détails d'implémentation de l'API Google.
"""
from abc import ABC, abstractmethod
from typing import Optional

class GoogleAuthPort(ABC):
    @abstractmethod
    async def get_credentials(self) -> dict:
        """
        Récupère les credentials d'authentification Google.
        
        Returns:
            dict: Les credentials nécessaires pour accéder aux API Google
        """
        pass

    @abstractmethod
    async def refresh_token(self) -> None:
        """
        Rafraîchit le token d'accès si nécessaire.
        Cette méthode doit être appelée avant chaque requête à l'API Google
        pour s'assurer que le token est valide.
        """
        pass

    @abstractmethod
    async def get_access_token(self) -> str:
        """
        Récupère le token d'accès actuel.
        
        Returns:
            str: Le token d'accès pour l'API Google
        """
        pass
