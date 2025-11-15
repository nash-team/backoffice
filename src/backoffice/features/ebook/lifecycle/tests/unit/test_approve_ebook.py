"""Unit tests for ApproveEbookUseCase using Chicago-style testing with fakes."""

from datetime import datetime

import pytest

from backoffice.features.ebook.lifecycle.domain.usecases.approve_ebook_usecase import (
    ApproveEbookUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError
from backoffice.features.shared.infrastructure.events.event_bus import EventBus


class FakeEbookRepository:
    """Fake implementation of EbookRepository for testing."""

    def __init__(self):
        self._ebooks = {}
        self._ebook_bytes = {}

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        return self._ebooks.get(ebook_id)

    async def save(self, ebook: Ebook) -> Ebook:
        self._ebooks[ebook.id] = ebook
        return ebook

    async def get_ebook_bytes(self, ebook_id: int) -> bytes | None:
        return self._ebook_bytes.get(ebook_id)

    async def save_ebook_bytes(self, ebook_id: int, ebook_bytes: bytes) -> None:
        self._ebook_bytes[ebook_id] = ebook_bytes

    def add_ebook(self, ebook: Ebook) -> None:
        """Helper method to add ebooks to the fake repository."""
        self._ebooks[ebook.id] = ebook
        # Add fake PDF bytes for testing
        self._ebook_bytes[ebook.id] = b"%PDF-1.4 fake pdf content"


class FakeFileStorage:
    """Fake implementation of FileStorage for testing."""

    def __init__(self, available: bool = True):
        self._available = available
        self._uploaded_files = {}

    def is_available(self) -> bool:
        return self._available

    async def upload_ebook(
        self, file_bytes: bytes, filename: str, metadata: dict
    ) -> dict[str, str]:
        storage_id = f"drive_id_{len(self._uploaded_files) + 1}"
        storage_url = f"https://drive.google.com/file/d/{storage_id}/view"
        self._uploaded_files[storage_id] = {
            "bytes": file_bytes,
            "filename": filename,
            "metadata": metadata,
        }
        return {"storage_id": storage_id, "storage_url": storage_url}


class TestApproveEbookUseCase:
    """Test cases for ApproveEbookUseCase using Chicago-style testing with fakes."""

    @pytest.fixture
    def ebook_repository(self):
        """Fake ebook repository."""
        return FakeEbookRepository()

    @pytest.fixture
    def file_storage(self):
        """Fake file storage."""
        return FakeFileStorage()

    @pytest.fixture
    def event_bus(self):
        """Fresh event bus for each test."""
        bus = EventBus()
        bus.clear()
        return bus

    @pytest.fixture
    def approve_ebook_usecase(self, ebook_repository, file_storage, event_bus):
        """ApproveEbookUseCase instance."""
        return ApproveEbookUseCase(ebook_repository, file_storage, event_bus)

    @pytest.fixture
    def draft_ebook(self):
        """Sample draft ebook with KDP-ready structure."""
        import base64
        from io import BytesIO

        from PIL import Image

        # Generate fake page image (2626x2626 for KDP)
        img = Image.new("RGB", (2626, 2626), (255, 255, 255))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return Ebook(
            id=1,
            title="Test Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.DRAFT,
            preview_url=None,
            drive_id=None,
            page_count=26,  # Required for KDP export
            structure_json={
                "pages_meta": [
                    {
                        "page_number": 0,
                        "title": "Cover",
                        "image_data_base64": img_base64,
                        "format": "PNG",
                        "color_mode": "COLOR",
                    }
                ]
                + [
                    {
                        "page_number": i + 1,
                        "title": f"Page {i + 1}",
                        "image_data_base64": img_base64,
                        "format": "PNG",
                        "color_mode": "BLACK_WHITE",
                    }
                    for i in range(24)  # 24 interior pages
                ]
                + [
                    {
                        "page_number": 25,
                        "title": "Back Cover",
                        "image_data_base64": img_base64,
                        "format": "PNG",
                        "color_mode": "BLACK_WHITE",
                    }
                ]
            },
        )

    @pytest.mark.asyncio
    async def test_approve_draft_ebook_success(
        self, approve_ebook_usecase, ebook_repository, draft_ebook
    ):
        """Should successfully approve a draft ebook and upload to Drive."""
        # Arrange
        ebook_repository.add_ebook(draft_ebook)

        # Act
        result = await approve_ebook_usecase.execute(1)

        # Assert
        assert result.status == EbookStatus.APPROVED
        assert result.id == draft_ebook.id
        assert result.title == draft_ebook.title
        assert result.author == draft_ebook.author
        # Check new dual Drive IDs (KDP Cover and KDP Interior)
        assert result.drive_id_cover is not None  # KDP Cover uploaded to Drive
        assert result.drive_id_interior is not None  # KDP Interior uploaded to Drive

        # Verify the ebook is persisted with correct status
        persisted_ebook = await ebook_repository.get_by_id(1)
        assert persisted_ebook.status == EbookStatus.APPROVED
        assert persisted_ebook.drive_id_cover is not None
        assert persisted_ebook.drive_id_interior is not None

    @pytest.mark.asyncio
    async def test_approve_emits_approved_event(
        self, approve_ebook_usecase, ebook_repository, draft_ebook, event_bus
    ):
        """Should emit EbookApprovedEvent when approval succeeds."""
        # Arrange
        ebook_repository.add_ebook(draft_ebook)
        events_received = []

        from backoffice.features.ebook.lifecycle.domain.events.ebook_approved_event import (
            EbookApprovedEvent,
        )
        from backoffice.features.shared.infrastructure.events.event_handler import EventHandler

        class TestHandler(EventHandler[EbookApprovedEvent]):
            async def handle(self, event: EbookApprovedEvent) -> None:
                events_received.append(event)

        event_bus.subscribe(EbookApprovedEvent, TestHandler())

        # Act
        await approve_ebook_usecase.execute(1)

        # Assert
        assert len(events_received) == 1
        event = events_received[0]
        assert event.ebook_id == 1
        assert event.title == "Test Ebook"
        assert event.drive_id is not None

    @pytest.mark.asyncio
    async def test_approve_nonexistent_ebook_raises_error(self, approve_ebook_usecase):
        """Should raise DomainError when ebook doesn't exist."""
        # Act & Assert
        with pytest.raises(DomainError, match="Ebook with ID 999 not found"):
            await approve_ebook_usecase.execute(999)

    @pytest.mark.asyncio
    async def test_approve_rejected_ebook_raises_error(
        self, approve_ebook_usecase, ebook_repository
    ):
        """Should raise DomainError when trying to approve rejected ebook."""
        # Arrange
        rejected_ebook = Ebook(
            id=3,
            title="Rejected Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.REJECTED,
            preview_url="http://example.com/preview",
            drive_id="test_drive_id",
        )
        ebook_repository.add_ebook(rejected_ebook)

        # Act & Assert
        with pytest.raises(DomainError, match="Ebook must be in DRAFT status"):
            await approve_ebook_usecase.execute(3)

    @pytest.mark.asyncio
    async def test_approve_already_approved_ebook_raises_error(
        self, approve_ebook_usecase, ebook_repository
    ):
        """Should raise DomainError when trying to approve already approved ebook."""
        # Arrange
        approved_ebook = Ebook(
            id=4,
            title="Already Approved",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.APPROVED,
            preview_url="http://example.com/preview",
            drive_id="test_drive_id",
        )
        ebook_repository.add_ebook(approved_ebook)

        # Act & Assert
        with pytest.raises(DomainError, match="Ebook must be in DRAFT status"):
            await approve_ebook_usecase.execute(4)

        # Verify the ebook status remains unchanged
        persisted_ebook = await ebook_repository.get_by_id(4)
        assert persisted_ebook.status == EbookStatus.APPROVED
