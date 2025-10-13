from abc import ABC, abstractmethod


class FileStoragePort(ABC):
    """Port for file storage operations (Google Drive, S3, etc.)"""

    @abstractmethod
    async def upload_ebook(
        self, file_bytes: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Upload ebook file to storage

        Args:
            file_bytes: The file content as bytes
            filename: Name for the uploaded file
            metadata: Optional metadata to attach to the file

        Returns:
            dict: Upload result with file ID, URL, etc.

        Raises:
            FileStorageError: If upload fails
        """
        pass

    @abstractmethod
    async def update_ebook(self, file_id: str, file_bytes: bytes, filename: str) -> dict[str, str]:
        """Update existing ebook file in storage

        Args:
            file_id: The storage-specific file identifier
            file_bytes: The new file content as bytes
            filename: Name for the updated file

        Returns:
            dict: Update result with storage_url, etc.

        Raises:
            FileStorageError: If update fails
        """
        pass

    @abstractmethod
    async def get_file_info(self, file_id: str) -> dict[str, str]:
        """Get information about a stored file

        Args:
            file_id: The storage-specific file identifier

        Returns:
            dict: File information (name, size, URL, etc.)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if storage service is available

        Returns:
            bool: True if storage can be used
        """
        pass
