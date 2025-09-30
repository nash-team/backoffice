import logging

from backoffice.domain.ports.file_storage_port import FileStoragePort
from backoffice.infrastructure.adapters.auth.google_auth import GoogleAuthService
from backoffice.infrastructure.adapters.sources.google_drive_adapter import GoogleDriveAdapter

logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    pass


class GoogleDriveStorageAdapter(FileStoragePort):
    """Google Drive storage adapter implementing FileStoragePort"""

    def __init__(self, credentials_path: str | None = None, default_user_email: str | None = None):
        self.credentials_path = credentials_path or "credentials/google_credentials.json"
        self.default_user_email = default_user_email  # Pour les cas simples (toi seul)
        self.drive_adapter = None
        self._initialize_drive()

    def _initialize_drive(self):
        """Initialize Google Drive adapter"""
        try:
            auth_service = GoogleAuthService(self.credentials_path)
            self.drive_adapter = GoogleDriveAdapter(auth_service)
            logger.info("Google Drive storage adapter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive adapter: {str(e)}")
            self.drive_adapter = None

    def is_available(self) -> bool:
        """Check if Google Drive storage is available"""
        return self.drive_adapter is not None

    async def upload_ebook(
        self, file_bytes: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Upload ebook to Google Drive"""
        if not self.is_available():
            raise FileStorageError("Google Drive storage is not available")

        try:
            logger.info(f"Uploading ebook to Google Drive: {filename}")

            # Extract title and author from metadata if provided
            title = metadata.get("title", "Unknown Title") if metadata else "Unknown Title"
            author = metadata.get("author", "Unknown Author") if metadata else "Unknown Author"

            # Use the existing upload_pdf_ebook method
            if self.drive_adapter is None:
                raise FileStorageError("Google Drive adapter not initialized")
            upload_result = await self.drive_adapter.upload_pdf_ebook(
                title=title, pdf_bytes=file_bytes, author=author
            )

            # Type safe result construction
            result: dict[str, str] = {
                "storage_id": str(upload_result.get("drive_id", "")),
                "storage_url": str(upload_result.get("preview_url", "")),
                "storage_status": "uploaded",
            }

            # Add storage info to result
            result.update(
                {
                    "storage_type": "google_drive",
                    "uploaded_by": self.default_user_email or "system",
                    "filename": filename,
                }
            )

            storage_id = result.get("storage_id", "unknown_id")
            logger.info(f"Successfully uploaded ebook to Google Drive: {storage_id}")
            return result

        except Exception as e:
            logger.error(f"Error uploading ebook to Google Drive: {str(e)}")
            raise FileStorageError(f"Failed to upload ebook: {str(e)}") from e

    async def update_ebook(self, file_id: str, file_bytes: bytes, filename: str) -> dict[str, str]:
        """Update existing ebook in Google Drive"""
        if not self.is_available():
            raise FileStorageError("Google Drive storage is not available")

        try:
            logger.info(f"Updating ebook in Google Drive: {file_id}")

            # Use GoogleDriveAdapter to update the file
            if self.drive_adapter is None:
                raise FileStorageError("Google Drive adapter not initialized")

            # For now, we'll use the update_pdf_ebook method (to be implemented)
            # or re-upload with same ID
            update_result = await self.drive_adapter.update_pdf_ebook(
                file_id=file_id, pdf_bytes=file_bytes
            )

            result: dict[str, str] = {
                "storage_id": str(file_id),
                "storage_url": str(update_result.get("preview_url", "")),
                "storage_status": "updated",
            }

            logger.info(f"Successfully updated ebook in Google Drive: {file_id}")
            return result

        except Exception as e:
            logger.error(f"Error updating ebook in Google Drive: {str(e)}")
            raise FileStorageError(f"Failed to update ebook: {str(e)}") from e

    async def get_file_info(self, file_id: str) -> dict[str, str]:
        """Get information about a file stored in Google Drive"""
        if not self.is_available():
            raise FileStorageError("Google Drive storage is not available")

        try:
            # This would need to be implemented in the GoogleDriveAdapter
            # For now, return basic structure
            return {"id": file_id, "status": "exists", "storage": "google_drive"}
        except Exception as e:
            logger.error(f"Error getting file info from Google Drive: {str(e)}")
            raise FileStorageError(f"Failed to get file info: {str(e)}") from e

    def get_storage_info(self) -> dict[str, str]:
        """Get information about the storage service"""
        return {
            "provider": "Google Drive",
            "available": str(self.is_available()),
            "credentials_path": self.credentials_path,
        }
