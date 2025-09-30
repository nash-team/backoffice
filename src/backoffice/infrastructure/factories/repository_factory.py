from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backoffice.domain.ports.content_generation_port import ContentGenerationPort
from backoffice.domain.ports.ebook.ebook_port import EbookPort
from backoffice.domain.ports.file_storage_port import FileStoragePort
from backoffice.domain.ports.image_generation_port import ImageGenerationPort
from backoffice.domain.ports.vectorization_port import VectorizationPort
from backoffice.infrastructure.adapters.google_drive_storage_adapter import (
    GoogleDriveStorageAdapter,
)
from backoffice.infrastructure.adapters.potrace_vectorizer import PotraceVectorizer
from backoffice.infrastructure.adapters.repositories.ebook_repository import (
    SqlAlchemyEbookRepository,
)
from backoffice.infrastructure.adapters.repositories.user_repository import SqlAlchemyUserRepository
from backoffice.infrastructure.database import get_db
from backoffice.infrastructure.factories.llm_adapter_factory import LLMAdapterFactory
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

    def get_image_generator(self, model: str | None = None) -> ImageGenerationPort:
        """Get image generation adapter using LLMAdapterFactory.

        Args:
            model: Optional explicit model to use

        Returns:
            ImageGenerationPort: Configured image generation adapter
        """
        return LLMAdapterFactory.create_image_adapter(model=model)

    def get_vectorizer(self) -> VectorizationPort:
        return PotraceVectorizer()

    def get_content_generator(self, model: str | None = None) -> ContentGenerationPort:
        """Get content generation adapter using LLMAdapterFactory.

        Args:
            model: Optional explicit model to use

        Returns:
            ContentGenerationPort: Configured content generation adapter
        """
        return LLMAdapterFactory.create_content_adapter(model=model)

    def get_file_storage(self) -> FileStoragePort:
        """Get file storage adapter (Google Drive)"""
        # GoogleDriveStorageAdapter creates its own auth service
        return GoogleDriveStorageAdapter()


def get_repository_factory(db: DatabaseDep) -> RepositoryFactory:
    return RepositoryFactory(db)
