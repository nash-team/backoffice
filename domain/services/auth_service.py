from datetime import timedelta
from typing import Optional
from domain.models.user import User, UserCreate
from domain.ports.auth.auth_port import AuthPort
from domain.ports.user.user_repository_port import UserRepositoryPort

class AuthService:
    def __init__(self, auth_port: AuthPort, user_repository: UserRepositoryPort):
        self.auth_port = auth_port
        self.user_repository = user_repository

    def register_user(self, user_create: UserCreate) -> User:
        # Vérifier si l'utilisateur existe déjà
        existing_user = self.user_repository.get_by_email(user_create.email)
        if existing_user:
            raise ValueError("Email déjà enregistré")
        
        # Créer le nouvel utilisateur
        hashed_password = self.auth_port.get_password_hash(user_create.password)
        user = User(
            email=user_create.email,
            username=user_create.username,
            hashed_password=hashed_password
        )
        return self.user_repository.save(user)

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        return self.auth_port.authenticate_user(email, password)

    def create_access_token(self, user: User) -> str:
        return self.auth_port.create_access_token({"sub": user.email})

    def get_current_user(self, token: str) -> User:
        return self.auth_port.get_current_user(token) 