from abc import ABC, abstractmethod
from typing import Optional

from domain.models.user import User


class AuthPort(ABC):
    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        pass

    @abstractmethod
    def get_password_hash(self, password: str) -> str:
        pass

    @abstractmethod
    def create_access_token(self, data: dict) -> str:
        pass

    @abstractmethod
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_current_user(self, token: str) -> User:
        pass
