"""Local file storage adapter for development/fallback mode."""

import logging
from pathlib import Path

from backoffice.features.ebook.shared.domain.ports.file_storage_port import FileStoragePort

logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    """Exception raised when file storage operations fail."""

    pass


class LocalFileStorageAdapter(FileStoragePort):
    """Local filesystem storage adapter implementing FileStoragePort.

    This adapter stores files on the local filesystem and is used as a fallback
    when Google Drive credentials are not available.

    Storage structure:
        storage/
        ├── ebooks/
        │   ├── {ebook_id}_full.pdf
        │   ├── {ebook_id}_cover.pdf
        │   └── {ebook_id}_interior.pdf
    """

    def __init__(self, storage_path: str | None = None):
        """Initialize local file storage adapter.

        Args:
            storage_path: Root path for file storage. Defaults to './storage'
        """
        self.storage_path = Path(storage_path or "./storage")
        self.ebooks_path = self.storage_path / "ebooks"
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Create storage directories if they don't exist."""
        try:
            self.ebooks_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local file storage initialized at: {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to initialize local storage: {e}")
            raise FileStorageError(f"Failed to initialize storage: {e}") from e

    def is_available(self) -> bool:
        """Check if local storage is available.

        Returns:
            bool: Always True for local storage (directories created on init)
        """
        return self.ebooks_path.exists() and self.ebooks_path.is_dir()

    async def upload_ebook(
        self, file_bytes: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Upload (save) ebook file to local storage.

        Args:
            file_bytes: The file content as bytes
            filename: Name for the file (e.g., "My_Ebook_Cover.pdf")
            metadata: Optional metadata (stored in filename for simplicity)

        Returns:
            dict: Upload result with local file path as storage_id

        Raises:
            FileStorageError: If file write fails
        """
        try:
            # Sanitize filename (remove special chars)
            safe_filename = "".join(c if c.isalnum() or c in "._- " else "_" for c in filename)
            file_path = self.ebooks_path / safe_filename

            # Write file
            file_path.write_bytes(file_bytes)

            logger.info(f"Saved ebook to local storage: {file_path}")

            return {
                "storage_id": str(file_path.absolute()),  # Use absolute path as ID
                "storage_url": f"file://{file_path.absolute()}",  # Local file URL
                "storage_status": "uploaded",
                "storage_type": "local_filesystem",
                "filename": safe_filename,
            }

        except Exception as e:
            logger.error(f"Failed to save ebook to local storage: {e}")
            raise FileStorageError(f"Failed to upload ebook: {e}") from e

    async def update_ebook(self, file_id: str, file_bytes: bytes, filename: str) -> dict[str, str]:
        """Update existing ebook file in local storage.

        Args:
            file_id: Path to the existing file (storage_id from upload)
            file_bytes: The new file content as bytes
            filename: Name for the updated file

        Returns:
            dict: Update result with local file path

        Raises:
            FileStorageError: If file update fails
        """
        try:
            file_path = Path(file_id)

            # Check if file exists
            if not file_path.exists():
                logger.warning(f"File not found for update: {file_id}, creating new file")

            # Overwrite file
            file_path.write_bytes(file_bytes)

            logger.info(f"Updated ebook in local storage: {file_path}")

            return {
                "storage_id": str(file_path.absolute()),
                "storage_url": f"file://{file_path.absolute()}",
                "storage_status": "updated",
                "storage_type": "local_filesystem",
            }

        except Exception as e:
            logger.error(f"Failed to update ebook in local storage: {e}")
            raise FileStorageError(f"Failed to update ebook: {e}") from e

    async def get_file_info(self, file_id: str) -> dict[str, str]:
        """Get information about a stored file.

        Args:
            file_id: Path to the file (storage_id)

        Returns:
            dict: File information (path, size, exists)

        Raises:
            FileStorageError: If file access fails
        """
        try:
            file_path = Path(file_id)

            if not file_path.exists():
                return {
                    "id": file_id,
                    "status": "not_found",
                    "storage": "local_filesystem",
                }

            return {
                "id": file_id,
                "status": "exists",
                "storage": "local_filesystem",
                "size_bytes": str(file_path.stat().st_size),
                "path": str(file_path.absolute()),
            }

        except Exception as e:
            logger.error(f"Failed to get file info from local storage: {e}")
            raise FileStorageError(f"Failed to get file info: {e}") from e

    def get_storage_info(self) -> dict[str, str]:
        """Get information about the storage service.

        Returns:
            dict: Storage provider information
        """
        return {
            "provider": "Local Filesystem",
            "available": str(self.is_available()),
            "storage_path": str(self.storage_path.absolute()),
            "ebooks_path": str(self.ebooks_path.absolute()),
        }
