import pytest
from datetime import datetime

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.usecases.reject_ebook import RejectEbookUseCase


class FakeEbookRepository:
    """Fake implementation of EbookRepository for testing"""

    def __init__(self):
        self._ebooks = {}

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        return self._ebooks.get(ebook_id)

    async def save(self, ebook: Ebook) -> Ebook:
        self._ebooks[ebook.id] = ebook
        return ebook

    def add_ebook(self, ebook: Ebook) -> None:
        """Helper method to add ebooks to the fake repository"""
        self._ebooks[ebook.id] = ebook


class TestRejectEbookUseCase:
    """Test cases for RejectEbookUseCase using Chicago-style testing with fakes"""

    @pytest.fixture
    def ebook_repository(self):
        """Fake ebook repository"""
        return FakeEbookRepository()

    @pytest.fixture
    def reject_ebook_usecase(self, ebook_repository):
        """RejectEbookUseCase instance"""
        return RejectEbookUseCase(ebook_repository)

    @pytest.fixture
    def pending_ebook(self):
        """Sample pending ebook"""
        return Ebook(
            id=1,
            title="Test Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.PENDING,
            preview_url="http://example.com/preview",
            drive_id="test_drive_id",
        )

    @pytest.fixture
    def approved_ebook(self):
        """Sample approved ebook"""
        return Ebook(
            id=2,
            title="Approved Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.APPROVED,
            preview_url="http://example.com/preview",
            drive_id="test_drive_id",
        )

    @pytest.fixture
    def draft_ebook(self):
        """Sample draft ebook"""
        return Ebook(
            id=3,
            title="Draft Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.DRAFT,
            preview_url="http://example.com/preview",
            drive_id="test_drive_id",
        )

    @pytest.mark.asyncio
    async def test_reject_pending_ebook_success(
        self, reject_ebook_usecase, ebook_repository, pending_ebook
    ):
        """Should successfully reject a pending ebook"""
        # Arrange
        ebook_repository.add_ebook(pending_ebook)

        # Act
        result = await reject_ebook_usecase.execute(1)

        # Assert
        assert result.status == EbookStatus.REJECTED
        assert result.id == pending_ebook.id
        assert result.title == pending_ebook.title
        assert result.author == pending_ebook.author

        # Verify the ebook is persisted with correct status
        persisted_ebook = await ebook_repository.get_by_id(1)
        assert persisted_ebook.status == EbookStatus.REJECTED

    @pytest.mark.asyncio
    async def test_reject_approved_ebook_success(
        self, reject_ebook_usecase, ebook_repository, approved_ebook
    ):
        """Should successfully reject an approved ebook"""
        # Arrange
        ebook_repository.add_ebook(approved_ebook)

        # Act
        result = await reject_ebook_usecase.execute(2)

        # Assert
        assert result.status == EbookStatus.REJECTED
        assert result.id == approved_ebook.id

        # Verify the ebook is persisted with correct status
        persisted_ebook = await ebook_repository.get_by_id(2)
        assert persisted_ebook.status == EbookStatus.REJECTED

    @pytest.mark.asyncio
    async def test_reject_nonexistent_ebook_raises_error(self, reject_ebook_usecase):
        """Should raise ValueError when ebook doesn't exist"""
        # Act & Assert
        with pytest.raises(ValueError, match="Ebook with id 999 not found"):
            await reject_ebook_usecase.execute(999)

    @pytest.mark.asyncio
    async def test_reject_draft_ebook_raises_error(
        self, reject_ebook_usecase, ebook_repository, draft_ebook
    ):
        """Should raise ValueError when trying to reject draft ebook"""
        # Arrange
        ebook_repository.add_ebook(draft_ebook)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot reject ebook with status DRAFT"):
            await reject_ebook_usecase.execute(3)

        # Verify the ebook status remains unchanged
        persisted_ebook = await ebook_repository.get_by_id(3)
        assert persisted_ebook.status == EbookStatus.DRAFT

    @pytest.mark.asyncio
    async def test_reject_already_rejected_ebook_raises_error(
        self, reject_ebook_usecase, ebook_repository
    ):
        """Should raise ValueError when trying to reject already rejected ebook"""
        # Arrange
        rejected_ebook = Ebook(
            id=4,
            title="Already Rejected",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.REJECTED,
            preview_url="http://example.com/preview",
            drive_id="test_drive_id",
        )
        ebook_repository.add_ebook(rejected_ebook)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot reject ebook with status REJECTED"):
            await reject_ebook_usecase.execute(4)

        # Verify the ebook status remains unchanged
        persisted_ebook = await ebook_repository.get_by_id(4)
        assert persisted_ebook.status == EbookStatus.REJECTED
