from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backoffice.domain.ports.content_generation_port import ContentGenerationPort
from backoffice.domain.ports.ebook.ebook_port import EbookPort
from backoffice.domain.ports.file_storage_port import FileStoragePort
from backoffice.features.generation_costs.domain.usecases.track_token_usage_usecase import (
    TrackTokenUsageUseCase,
)
from backoffice.features.generation_costs.infrastructure.adapters.token_tracker_repository import (
    TokenTrackerRepository,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus
from backoffice.features.shared.infrastructure.events.event_bus_singleton import get_event_bus
from backoffice.infrastructure.adapters.google_drive_storage_adapter import (
    GoogleDriveStorageAdapter,
)
from backoffice.infrastructure.adapters.repositories.ebook_repository import (
    SqlAlchemyEbookRepository,
)
from backoffice.infrastructure.database import get_async_db, get_db
from backoffice.infrastructure.factories.llm_adapter_factory import LLMAdapterFactory

# Type alias pour l'injection de dépendance propre
DatabaseDep = Annotated[Session, Depends(get_db)]
AsyncDatabaseDep = Annotated[AsyncSession, Depends(get_async_db)]


class RepositoryFactory:
    def __init__(self, db: Session):
        self.db = db

    def get_ebook_repository(self) -> EbookPort:
        return SqlAlchemyEbookRepository(self.db)

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

    def get_event_bus(self) -> EventBus:
        """Get the global EventBus instance."""
        return get_event_bus()

    # Note: TrackTokenUsageUseCase requires async DB, use AsyncRepositoryFactory instead


class AsyncRepositoryFactory:
    """Async version of RepositoryFactory for async DB operations.

    Used by features that require async database access (e.g., generation_costs).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def get_event_bus(self) -> EventBus:
        """Get the global EventBus instance."""
        return get_event_bus()

    def get_track_token_usage_usecase(self) -> TrackTokenUsageUseCase:
        """Get TrackTokenUsageUseCase with async dependencies injected."""
        token_tracker = TokenTrackerRepository(self.db)
        event_bus = self.get_event_bus()
        return TrackTokenUsageUseCase(token_tracker, event_bus)

    def get_ebook_repository(self) -> EbookPort:
        """Get ebook repository (uses sync DB session for now)."""
        # TODO: Create async version of EbookRepository
        # For now, create a sync session from the async engine
        from backoffice.infrastructure.database import get_db

        sync_db = next(get_db())
        return SqlAlchemyEbookRepository(sync_db)

    def get_file_storage(self) -> FileStoragePort:
        """Get file storage adapter (Google Drive)"""
        return GoogleDriveStorageAdapter()


def get_repository_factory(db: DatabaseDep) -> RepositoryFactory:
    return RepositoryFactory(db)


def get_async_repository_factory(db: AsyncDatabaseDep) -> AsyncRepositoryFactory:
    return AsyncRepositoryFactory(db)
