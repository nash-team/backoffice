from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backoffice.domain.ports.ebook.ebook_port import EbookPort
from backoffice.domain.usecases.create_ebook import EbookProcessor
from backoffice.infrastructure.adapters.openai_ebook_processor import OpenAIEbookProcessor
from backoffice.infrastructure.adapters.repositories.ebook_repository import (
    SqlAlchemyEbookRepository,
)
from backoffice.infrastructure.adapters.repositories.user_repository import SqlAlchemyUserRepository
from backoffice.infrastructure.database import get_db
from backoffice.infrastructure.ports.repositories.user_repository_port import UserRepositoryPort

# Type alias pour l'injection de dépendance propre
DatabaseDep = Annotated[Session, Depends(get_db)]


class RepositoryFactory:
    def __init__(self, db: Session):
        self.db = db

    def get_ebook_repository(self) -> EbookPort:
        return SqlAlchemyEbookRepository(self.db)

    def get_user_repository(self) -> UserRepositoryPort:
        return SqlAlchemyUserRepository(self.db)

    def get_ebook_processor(self) -> EbookProcessor:
        return OpenAIEbookProcessor()


def get_repository_factory(db: DatabaseDep) -> RepositoryFactory:
    return RepositoryFactory(db)
