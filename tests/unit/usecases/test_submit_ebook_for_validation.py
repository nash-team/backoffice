"""Unit tests for SubmitEbookForValidationUseCase"""

from datetime import datetime

import pytest

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.usecases.submit_ebook_for_validation import (
    SubmitEbookForValidationUseCase,
)
from backoffice.infrastructure.adapters.in_memory_ebook_repository import (
    InMemoryEbookRepository,
)


@pytest.mark.asyncio
class TestSubmitEbookForValidationUseCase:
    """Test suite for submit ebook for validation use case"""

    async def test_submit_draft_ebook_successfully(self):
        """Should transition DRAFT ebook to PENDING status"""
        # Given
        draft_ebook = Ebook(
            id=1,
            title="Test Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.DRAFT,
            drive_id="test_drive_id",
            preview_url="https://drive.google.com/file/d/test_drive_id/preview",
        )

        ebook_repo = InMemoryEbookRepository()
        await ebook_repo.save(draft_ebook)

        usecase = SubmitEbookForValidationUseCase(ebook_repo)

        # When
        result = await usecase.execute(draft_ebook.id)

        # Then
        assert result.id == draft_ebook.id
        assert result.status == EbookStatus.PENDING
        assert result.title == draft_ebook.title
        assert result.author == draft_ebook.author

        # Verify persistence
        persisted_ebook = await ebook_repo.get_by_id(draft_ebook.id)
        assert persisted_ebook is not None
        assert persisted_ebook.status == EbookStatus.PENDING

    async def test_submit_ebook_not_found(self):
        """Should raise ValueError when ebook not found"""
        # Given
        ebook_repo = InMemoryEbookRepository()
        usecase = SubmitEbookForValidationUseCase(ebook_repo)

        # When/Then
        with pytest.raises(ValueError, match="Ebook with id 999 not found"):
            await usecase.execute(999)

    async def test_submit_non_draft_ebook_fails(self):
        """Should raise ValueError when trying to submit non-DRAFT ebook"""
        # Given
        pending_ebook = Ebook(
            id=1,
            title="Test Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.PENDING,
            drive_id="test_drive_id",
            preview_url="https://drive.google.com/file/d/test_drive_id/preview",
        )

        ebook_repo = InMemoryEbookRepository()
        await ebook_repo.save(pending_ebook)

        usecase = SubmitEbookForValidationUseCase(ebook_repo)

        # When/Then
        with pytest.raises(ValueError, match="Cannot submit ebook with status PENDING"):
            await usecase.execute(pending_ebook.id)

        # Verify ebook status unchanged
        persisted_ebook = await ebook_repo.get_by_id(pending_ebook.id)
        assert persisted_ebook.status == EbookStatus.PENDING

    async def test_submit_ebook_without_pdf_fails(self):
        """Should raise ValueError when ebook doesn't have generated PDF"""
        # Given
        draft_ebook = Ebook(
            id=1,
            title="Test Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.DRAFT,
            drive_id=None,  # No PDF generated
            preview_url=None,
        )

        ebook_repo = InMemoryEbookRepository()
        await ebook_repo.save(draft_ebook)

        usecase = SubmitEbookForValidationUseCase(ebook_repo)

        # When/Then
        with pytest.raises(ValueError, match="Cannot submit ebook without a generated PDF"):
            await usecase.execute(draft_ebook.id)

        # Verify ebook status unchanged
        persisted_ebook = await ebook_repo.get_by_id(draft_ebook.id)
        assert persisted_ebook.status == EbookStatus.DRAFT

    async def test_submit_approved_ebook_fails(self):
        """Should raise ValueError when trying to submit APPROVED ebook"""
        # Given
        approved_ebook = Ebook(
            id=1,
            title="Test Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.APPROVED,
            drive_id="test_drive_id",
            preview_url="https://drive.google.com/file/d/test_drive_id/preview",
        )

        ebook_repo = InMemoryEbookRepository()
        await ebook_repo.save(approved_ebook)

        usecase = SubmitEbookForValidationUseCase(ebook_repo)

        # When/Then
        with pytest.raises(ValueError, match="Cannot submit ebook with status APPROVED"):
            await usecase.execute(approved_ebook.id)

    async def test_submit_rejected_ebook_fails(self):
        """Should raise ValueError when trying to submit REJECTED ebook"""
        # Given
        rejected_ebook = Ebook(
            id=1,
            title="Test Ebook",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.REJECTED,
            drive_id="test_drive_id",
            preview_url="https://drive.google.com/file/d/test_drive_id/preview",
        )

        ebook_repo = InMemoryEbookRepository()
        await ebook_repo.save(rejected_ebook)

        usecase = SubmitEbookForValidationUseCase(ebook_repo)

        # When/Then
        with pytest.raises(ValueError, match="Cannot submit ebook with status REJECTED"):
            await usecase.execute(rejected_ebook.id)
