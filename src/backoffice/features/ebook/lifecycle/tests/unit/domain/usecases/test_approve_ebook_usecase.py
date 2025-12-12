"""Unit tests for ApproveEbookUseCase (Chicago style with fakes)."""

import base64
from datetime import datetime

import pytest

from backoffice.features.ebook.lifecycle.domain.usecases.approve_ebook_usecase import (
    ApproveEbookUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    EbookConfig,
    EbookStatus,
)
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# === Fakes ===


class FakeEbookRepository:
    """Fake ebook repository for testing."""

    def __init__(self):
        self._ebooks: dict[int, Ebook] = {}
        self.save_count = 0

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        return self._ebooks.get(ebook_id)

    async def save(self, ebook: Ebook) -> Ebook:
        self.save_count += 1
        self._ebooks[ebook.id] = ebook
        return ebook

    def add_ebook(self, ebook: Ebook) -> None:
        """Helper to add ebook to fake repo."""
        self._ebooks[ebook.id] = ebook


class FakeFileStorage:
    """Fake file storage for testing."""

    def __init__(self, mode: str = "succeed"):
        """Initialize fake storage.

        Args:
            mode: Behavior mode (succeed, unavailable, fail_upload)
        """
        self.mode = mode
        self.upload_count = 0
        self.uploads: list[dict] = []

    def is_available(self) -> bool:
        return self.mode != "unavailable"

    async def upload_ebook(self, file_bytes: bytes, filename: str, metadata: dict | None = None) -> dict[str, str]:
        self.upload_count += 1
        self.uploads.append({"filename": filename, "size": len(file_bytes), "metadata": metadata})

        if self.mode == "fail_upload":
            raise Exception("Fake upload failure")

        return {
            "storage_id": f"fake_drive_id_{self.upload_count}",
            "storage_url": f"https://drive.google.com/fake/{self.upload_count}",
        }


class FakeExportToKDPUseCase:
    """Fake for ExportToKDPUseCase."""

    def __init__(self, should_fail: bool = False, pdf_size: int = 50000):
        self.should_fail = should_fail
        self.pdf_size = pdf_size
        self.call_count = 0

    async def execute(self, ebook_id: int, preview_mode: bool = False) -> bytes:
        self.call_count += 1
        if self.should_fail:
            raise Exception("Fake KDP export failure")
        return b"%PDF-1.7 fake kdp cover content" + b"x" * self.pdf_size


class FakeExportToKDPInteriorUseCase:
    """Fake for ExportToKDPInteriorUseCase."""

    def __init__(self, should_fail: bool = False, pdf_size: int = 100000):
        self.should_fail = should_fail
        self.pdf_size = pdf_size
        self.call_count = 0

    async def execute(self, ebook_id: int, preview_mode: bool = False) -> bytes:
        self.call_count += 1
        if self.should_fail:
            raise Exception("Fake KDP interior export failure")
        return b"%PDF-1.7 fake kdp interior content" + b"x" * self.pdf_size


# === Test Fixtures ===


def _create_sample_ebook(
    ebook_id: int = 1,
    status: EbookStatus = EbookStatus.DRAFT,
    page_count: int = 27,
    with_structure: bool = True,
) -> Ebook:
    """Create a sample ebook for testing."""
    fake_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    fake_b64 = base64.b64encode(fake_png).decode("utf-8")

    structure_json = None
    if with_structure:
        structure_json = {
            "pages_meta": [
                {"page_number": 0, "title": "Cover", "image_data_base64": fake_b64},
                *[{"page_number": i, "title": f"Page {i}", "image_data_base64": fake_b64} for i in range(1, page_count - 1)],
                {"page_number": page_count - 1, "title": "Back Cover", "image_data_base64": fake_b64},
            ]
        }

    return Ebook(
        id=ebook_id,
        title="Test Coloring Book",
        author="Test Author",
        created_at=datetime.now(),
        status=status,
        config=EbookConfig(ebook_type="coloring_book", number_of_pages=25),
        page_count=page_count,
        structure_json=structure_json,
    )


# === Tests ===


class TestApproveEbookUseCase:
    """Test cases for ApproveEbookUseCase."""

    @pytest.fixture
    def ebook_repository(self):
        return FakeEbookRepository()

    @pytest.fixture
    def file_storage(self):
        return FakeFileStorage(mode="succeed")

    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.fixture
    def use_case(self, ebook_repository, file_storage, event_bus):
        return ApproveEbookUseCase(
            ebook_repository=ebook_repository,
            file_storage=file_storage,
            event_bus=event_bus,
        )

    async def test_approve_draft_ebook_success(self, use_case, ebook_repository, file_storage):
        """Test approving a DRAFT ebook succeeds."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT)
        ebook_repository.add_ebook(ebook)

        # Act
        result = await use_case.execute(ebook_id=1)

        # Assert
        assert result.status == EbookStatus.APPROVED
        assert result.drive_id_cover is not None
        assert result.drive_id_interior is not None
        assert file_storage.upload_count == 2  # Cover + Interior
        assert ebook_repository.save_count == 1

    async def test_approve_nonexistent_ebook_fails(self, use_case):
        """Test approving nonexistent ebook raises error."""
        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=999)

        assert exc_info.value.code == ErrorCode.EBOOK_NOT_FOUND
        assert "999" in str(exc_info.value.message)

    async def test_approve_already_approved_ebook_fails(self, use_case, ebook_repository):
        """Test approving already APPROVED ebook fails."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)
        ebook_repository.add_ebook(ebook)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "APPROVED" in str(exc_info.value.message)

    async def test_approve_rejected_ebook_fails(self, use_case, ebook_repository):
        """Test approving REJECTED ebook fails."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.REJECTED)
        ebook_repository.add_ebook(ebook)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    async def test_approve_ebook_without_structure_fails(self, use_case, ebook_repository):
        """Test approving ebook without structure fails."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT, with_structure=False)
        ebook_repository.add_ebook(ebook)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "structure" in str(exc_info.value.message).lower()

    async def test_approve_ebook_storage_unavailable_fails(self, ebook_repository, event_bus):
        """Test approving ebook when storage is unavailable fails."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT)
        ebook_repository.add_ebook(ebook)

        file_storage = FakeFileStorage(mode="unavailable")
        use_case = ApproveEbookUseCase(
            ebook_repository=ebook_repository,
            file_storage=file_storage,
            event_bus=event_bus,
        )

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1)

        assert exc_info.value.code == ErrorCode.PROVIDER_UNAVAILABLE
        assert "storage" in str(exc_info.value.message).lower()

    async def test_approve_ebook_upload_count(self, use_case, ebook_repository, file_storage):
        """Test that approval uploads both Cover and Interior PDFs."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT)
        ebook_repository.add_ebook(ebook)

        # Act
        await use_case.execute(ebook_id=1)

        # Assert
        assert file_storage.upload_count == 2
        assert any("Cover" in u["filename"] for u in file_storage.uploads)
        assert any("Interior" in u["filename"] for u in file_storage.uploads)

    async def test_approve_ebook_sets_drive_ids(self, use_case, ebook_repository):
        """Test that approval sets both cover and interior drive IDs."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT)
        ebook_repository.add_ebook(ebook)

        # Act
        result = await use_case.execute(ebook_id=1)

        # Assert
        assert result.drive_id_cover == "fake_drive_id_1"
        assert result.drive_id_interior == "fake_drive_id_2"
