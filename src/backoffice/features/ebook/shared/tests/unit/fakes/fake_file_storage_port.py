"""Fake file storage port for testing."""

from backoffice.features.ebook.shared.domain.ports.file_storage_port import FileStoragePort


class FakeFileStoragePort(FileStoragePort):
    """Fake file storage port for testing.

    Configurable behavior:
    - succeed: Upload/update operations succeed
    - fail_upload: Upload fails
    - fail_update: Update fails
    - unavailable: Storage is not available
    """

    def __init__(self, mode: str = "succeed"):
        """Initialize fake file storage port.

        Args:
            mode: Behavior mode (succeed, fail_upload, fail_update, unavailable)
        """
        self.mode = mode
        self.uploads: dict[str, dict[str, bytes | str]] = {}  # storage_id -> {file_bytes, filename, metadata}
        self.upload_count = 0
        self.update_count = 0

    def is_available(self) -> bool:
        """Check if storage service is available."""
        return self.mode != "unavailable"

    async def upload_ebook(self, file_bytes: bytes, filename: str, metadata: dict[str, str] | None = None) -> dict[str, str]:
        """Upload ebook file to fake storage."""
        self.upload_count += 1

        if self.mode == "fail_upload":
            raise Exception("Fake upload failure")

        # Generate fake storage ID
        storage_id = f"fake_storage_id_{self.upload_count}"

        # Store upload
        self.uploads[storage_id] = {
            "file_bytes": file_bytes,
            "filename": filename,
            "metadata": metadata or {},
        }

        return {
            "storage_id": storage_id,
            "storage_url": f"https://fake-storage.example.com/{storage_id}",
            "storage_status": "uploaded",
            "storage_type": "fake_storage",
            "filename": filename,
        }

    async def update_ebook(self, file_id: str, file_bytes: bytes, filename: str) -> dict[str, str]:
        """Update existing ebook file in fake storage."""
        self.update_count += 1

        if self.mode == "fail_update":
            raise Exception("Fake update failure")

        # Update existing upload
        if file_id in self.uploads:
            self.uploads[file_id]["file_bytes"] = file_bytes
            self.uploads[file_id]["filename"] = filename
        else:
            # Create new entry if not found
            self.uploads[file_id] = {
                "file_bytes": file_bytes,
                "filename": filename,
                "metadata": {},
            }

        return {
            "storage_id": file_id,
            "storage_url": f"https://fake-storage.example.com/{file_id}",
            "storage_status": "updated",
            "storage_type": "fake_storage",
        }

    async def get_file_info(self, file_id: str) -> dict[str, str]:
        """Get information about a stored file."""
        if file_id not in self.uploads:
            return {
                "id": file_id,
                "status": "not_found",
                "storage": "fake_storage",
            }

        upload = self.uploads[file_id]
        file_bytes = upload["file_bytes"]
        size = len(file_bytes) if isinstance(file_bytes, bytes) else 0

        return {
            "id": file_id,
            "status": "exists",
            "storage": "fake_storage",
            "size_bytes": str(size),
            "filename": str(upload["filename"]),
        }
