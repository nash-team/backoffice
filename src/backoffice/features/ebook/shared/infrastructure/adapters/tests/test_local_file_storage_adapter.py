"""Unit tests for LocalFileStorageAdapter."""

import shutil
import tempfile
from pathlib import Path

import pytest

from backoffice.features.ebook.shared.infrastructure.adapters.local_file_storage_adapter import (
    LocalFileStorageAdapter,
)


class TestLocalFileStorageAdapter:
    """Test cases for LocalFileStorageAdapter."""

    @pytest.fixture
    def temp_storage_path(self):
        """Create temporary directory for test storage."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def adapter(self, temp_storage_path):
        """Create adapter with temporary storage."""
        return LocalFileStorageAdapter(storage_path=temp_storage_path)

    def test_adapter_initialization_creates_directories(self, temp_storage_path):
        """Test that adapter creates storage directories on init."""
        adapter = LocalFileStorageAdapter(storage_path=temp_storage_path)

        assert adapter.storage_path.exists()
        assert adapter.ebooks_path.exists()
        assert adapter.ebooks_path.is_dir()

    def test_is_available_returns_true_when_initialized(self, adapter):
        """Test that is_available returns True after initialization."""
        assert adapter.is_available() is True

    async def test_upload_ebook_success(self, adapter):
        """Test successful ebook upload."""
        file_bytes = b"%PDF-1.4 fake pdf content"
        filename = "Test_Ebook.pdf"
        metadata = {"title": "Test Ebook", "author": "Test Author"}

        result = await adapter.upload_ebook(
            file_bytes=file_bytes,
            filename=filename,
            metadata=metadata,
        )

        # Check result structure
        assert "storage_id" in result
        assert "storage_url" in result
        assert result["storage_status"] == "uploaded"
        assert result["storage_type"] == "local_filesystem"
        assert result["filename"] == filename

        # Check file was actually written
        storage_id = result["storage_id"]
        file_path = Path(storage_id)
        assert file_path.exists()
        assert file_path.read_bytes() == file_bytes

    async def test_upload_ebook_sanitizes_filename(self, adapter):
        """Test that upload sanitizes special characters in filename."""
        file_bytes = b"test content"
        filename = "Test/Ebook:With*Special?.pdf"  # Invalid chars

        result = await adapter.upload_ebook(
            file_bytes=file_bytes,
            filename=filename,
        )

        # Check that filename was sanitized
        safe_filename = result["filename"]
        assert "/" not in safe_filename
        assert ":" not in safe_filename
        assert "*" not in safe_filename
        assert "?" not in safe_filename

    async def test_update_ebook_existing_file(self, adapter):
        """Test updating an existing file."""
        # First upload
        original_bytes = b"original content"
        filename = "Test.pdf"
        upload_result = await adapter.upload_ebook(
            file_bytes=original_bytes,
            filename=filename,
        )
        storage_id = upload_result["storage_id"]

        # Update file
        new_bytes = b"updated content"
        update_result = await adapter.update_ebook(
            file_id=storage_id,
            file_bytes=new_bytes,
            filename=filename,
        )

        # Check update result
        assert update_result["storage_id"] == storage_id
        assert update_result["storage_status"] == "updated"

        # Check file content was updated
        file_path = Path(storage_id)
        assert file_path.read_bytes() == new_bytes

    async def test_update_ebook_nonexistent_file_creates_new(self, adapter):
        """Test that updating a non-existent file creates it."""
        file_bytes = b"new content"
        fake_id = str(adapter.ebooks_path / "nonexistent.pdf")
        filename = "New_File.pdf"

        await adapter.update_ebook(
            file_id=fake_id,
            file_bytes=file_bytes,
            filename=filename,
        )

        # Check file was created
        file_path = Path(fake_id)
        assert file_path.exists()
        assert file_path.read_bytes() == file_bytes

    async def test_get_file_info_existing_file(self, adapter):
        """Test getting info for an existing file."""
        # Upload file
        file_bytes = b"test content"
        filename = "Test.pdf"
        upload_result = await adapter.upload_ebook(
            file_bytes=file_bytes,
            filename=filename,
        )
        storage_id = upload_result["storage_id"]

        # Get file info
        info = await adapter.get_file_info(file_id=storage_id)

        assert info["id"] == storage_id
        assert info["status"] == "exists"
        assert info["storage"] == "local_filesystem"
        assert int(info["size_bytes"]) == len(file_bytes)

    async def test_get_file_info_nonexistent_file(self, adapter):
        """Test getting info for a non-existent file."""
        fake_id = str(adapter.ebooks_path / "nonexistent.pdf")

        info = await adapter.get_file_info(file_id=fake_id)

        assert info["id"] == fake_id
        assert info["status"] == "not_found"
        assert info["storage"] == "local_filesystem"

    def test_get_storage_info(self, adapter):
        """Test getting storage provider information."""
        info = adapter.get_storage_info()

        assert info["provider"] == "Local Filesystem"
        assert info["available"] == "True"
        assert "storage_path" in info
        assert "ebooks_path" in info

    async def test_upload_multiple_files(self, adapter):
        """Test uploading multiple files."""
        files = [
            (b"content 1", "file1.pdf"),
            (b"content 2", "file2.pdf"),
            (b"content 3", "file3.pdf"),
        ]

        results = []
        for file_bytes, filename in files:
            result = await adapter.upload_ebook(
                file_bytes=file_bytes,
                filename=filename,
            )
            results.append(result)

        # Check all files were created
        for result in results:
            file_path = Path(result["storage_id"])
            assert file_path.exists()

        # Check all files have unique IDs
        storage_ids = [r["storage_id"] for r in results]
        assert len(storage_ids) == len(set(storage_ids))  # All unique
