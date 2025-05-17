from abc import ABC, abstractmethod
from typing import Optional
from domain.models.user import User, UserCreate

class UserRepositoryPort(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def create(self, user: UserCreate) -> User:
        pass

    @abstractmethod
    def save(self, user: User) -> User:
        pass 