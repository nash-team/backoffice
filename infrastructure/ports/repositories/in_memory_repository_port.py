"""
Ce port définit l'interface pour les repositories en mémoire.
Il spécifie les contrats que doivent respecter toutes les implémentations
de stockage en mémoire, principalement utilisées pour les tests.

Le port suit le principe d'inversion de dépendance en définissant une abstraction
que le domaine peut utiliser sans connaître les détails d'implémentation du stockage en mémoire.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class InMemoryRepositoryPort(ABC, Generic[T]):
    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        Crée une nouvelle entité en mémoire.
        
        Args:
            entity: L'entité à créer
            
        Returns:
            T: L'entité créée avec son ID
            
        Raises:
            DuplicateEntityError: Si une entité similaire existe déjà
        """
        pass

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        """
        Récupère une entité par son ID.
        
        Args:
            id: L'ID de l'entité à rechercher
            
        Returns:
            Optional[T]: L'entité trouvée ou None
        """
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """
        Met à jour une entité existante.
        
        Args:
            entity: L'entité à mettre à jour
            
        Returns:
            T: L'entité mise à jour
            
        Raises:
            EntityNotFoundError: Si l'entité n'existe pas
        """
        pass

    @abstractmethod
    async def delete(self, id: int) -> None:
        """
        Supprime une entité.
        
        Args:
            id: L'ID de l'entité à supprimer
            
        Raises:
            EntityNotFoundError: Si l'entité n'existe pas
        """
        pass

    @abstractmethod
    async def list_all(self) -> List[T]:
        """
        Liste toutes les entités.
        
        Returns:
            List[T]: La liste de toutes les entités
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """
        Vide le repository en mémoire.
        Utile pour les tests.
        """
        pass 