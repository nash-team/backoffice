from sqlalchemy.orm import Session
from typing import Optional
from domain.models.user import User, UserCreate
from domain.ports.user.user_repository_port import UserRepositoryPort
from infrastructure.models.user_model import UserModel

class SqlAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
        if not db_user:
            return None
        return self._to_domain(db_user)

    def create(self, user: UserCreate) -> User:
        db_user = UserModel(
            email=user.email,
            username=user.username,
            hashed_password=user.password  # Le mot de passe doit être hashé avant
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return self._to_domain(db_user)

    def save(self, user: User) -> User:
        db_user = UserModel(
            email=user.email,
            username=user.username,
            hashed_password=user.hashed_password
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return self._to_domain(db_user)

    def _to_domain(self, db_user: UserModel) -> User:
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            hashed_password=db_user.hashed_password,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        ) 