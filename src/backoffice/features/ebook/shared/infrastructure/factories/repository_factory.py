import logging
import os
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.ports.file_storage_port import FileStoragePort
from backoffice.features.ebook.shared.infrastructure.adapters.google_drive_storage_adapter import (
    GoogleDriveStorageAdapter,
)
from backoffice.features.ebook.shared.infrastructure.adapters.local_file_storage_adapter import (
    LocalFileStorageAdapter,
)
from backoffice.features.ebook.shared.infrastructure.repositories.ebook_repository import (
    SqlAlchemyEbookRepository,
)
from backoffice.features.shared.infrastructure.database import get_db
from backoffice.features.shared.infrastructure.events.event_bus import EventBus
from backoffice.features.shared.infrastructure.events.event_bus_singleton import get_event_bus

logger = logging.getLogger(__name__)

# Type alias pour l'injection de dépendance propre
DatabaseDep = Annotated[Session, Depends(get_db)]


class RepositoryFactory:
    def __init__(self, db: Session):
        self.db = db

    def get_ebook_repository(self) -> EbookPort:
        return SqlAlchemyEbookRepository(self.db)

    def get_file_storage(self) -> FileStoragePort:
        """Get file storage adapter (auto-detects Google Drive or falls back to local).

        Priority:
        1. Try Google Drive if credentials are configured
        2. Fall back to local filesystem storage if Drive is unavailable

        Returns:
            FileStoragePort: Storage adapter (Drive or local)
        """
        # Check if Google Drive credentials exist
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")
        use_drive = os.path.exists(credentials_path)

        if use_drive:
            try:
                drive_adapter = GoogleDriveStorageAdapter()
                if drive_adapter.is_available():
                    logger.info("✅ Using Google Drive storage (credentials found)")
                    return drive_adapter
                else:
                    logger.warning("⚠️ Google Drive credentials found but Drive unavailable, " "falling back to local storage")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Google Drive: {e}, falling back to local storage")

        # Fall back to local storage
        storage_path = os.getenv("LOCAL_STORAGE_PATH", "./storage")
        logger.info(f"✅ Using local file storage at: {storage_path}")
        return LocalFileStorageAdapter(storage_path=storage_path)

    def get_event_bus(self) -> EventBus:
        """Get the global EventBus instance."""
        return get_event_bus()


def get_repository_factory(db: DatabaseDep) -> RepositoryFactory:
    return RepositoryFactory(db)
