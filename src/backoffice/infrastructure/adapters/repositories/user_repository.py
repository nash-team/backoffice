from sqlalchemy.orm import Session

from backoffice.domain.entities.user import User
from backoffice.infrastructure.models.user_model import UserModel
from backoffice.infrastructure.ports.repositories.user_repository_port import UserRepositoryPort


class SqlAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    async def create(self, user: User) -> User:
        db_user = UserModel(
            email=user.email,
            username=user.username,
            hashed_password=user.hashed_password,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return self._to_domain(db_user)

    async def get_by_email(self, email: str) -> User | None:
        db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
        if not db_user:
            return None
        return self._to_domain(db_user)

    async def get_by_id(self, id: int) -> User | None:
        db_user = self.db.query(UserModel).filter(UserModel.id == id).first()
        if not db_user:
            return None
        return self._to_domain(db_user)

    async def update(self, user: User) -> User:
        db_user = self.db.query(UserModel).filter(UserModel.id == user.id).first()
        if not db_user:
            raise ValueError(f"User with id {user.id} not found")

        db_user.email = user.email
        db_user.username = user.username
        db_user.hashed_password = user.hashed_password
        self.db.commit()
        self.db.refresh(db_user)
        return self._to_domain(db_user)

    async def delete(self, id: int) -> None:
        db_user = self.db.query(UserModel).filter(UserModel.id == id).first()
        if not db_user:
            raise ValueError(f"User with id {id} not found")
        self.db.delete(db_user)
        self.db.commit()

    async def list_all(self) -> list[User]:
        db_users = self.db.query(UserModel).all()
        return [self._to_domain(user) for user in db_users]

    def _to_domain(self, db_user: UserModel) -> User:
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            hashed_password=db_user.hashed_password,
            is_admin=db_user.is_active,
        )
