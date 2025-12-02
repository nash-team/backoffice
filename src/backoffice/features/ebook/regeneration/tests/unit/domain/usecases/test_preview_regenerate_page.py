"""Tests for PreviewRegeneratePageUseCase."""

import base64
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from backoffice.features.ebook.regeneration.domain.usecases.preview_regenerate_page import (
    PreviewRegeneratePageUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode


@pytest.mark.asyncio
async def test_preview_regenerate_page_success():
    """Test successful preview regeneration of a content page."""
    # Arrange
    ebook_id = 1
    page_index = 1
    fake_ebook = Ebook(
        id=ebook_id,
        title="Test Coloring Book",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.DRAFT,
        theme_id="dinosaurs",
        audience="6-8",
    )

    # Simulate existing structure with cover + pages + back cover
    cover_bytes = b"fake_cover_image"
    page1_bytes = b"old_page_1_image"
    page2_bytes = b"fake_page_2_image"
    back_cover_bytes = b"fake_back_cover_image"

    fake_ebook.structure_json = {
        "pages_meta": [
            {
                "page_number": 0,
                "title": "Cover",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(cover_bytes).decode(),
            },
            {
                "page_number": 1,
                "title": "Page 1",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(page1_bytes).decode(),
            },
            {
                "page_number": 2,
                "title": "Page 2",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(page2_bytes).decode(),
            },
            {
                "page_number": 3,
                "title": "Back Cover",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(back_cover_bytes).decode(),
            },
        ]
    }

    # Mock dependencies
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook

    mock_page_service = AsyncMock()
    new_page_bytes = b"new_preview_page_image"
    mock_page_service.generate_single_page.return_value = new_page_bytes

    # Act
    use_case = PreviewRegeneratePageUseCase(
        ebook_repository=mock_repo,
        page_service=mock_page_service,
    )

    result = await use_case.execute(ebook_id=ebook_id, page_index=page_index)

    # Assert
    assert result["page_index"] == page_index
    assert "image_base64" in result
    assert result["image_base64"] == base64.b64encode(new_page_bytes).decode("utf-8")
    assert "prompt_used" in result

    # Verify no save was called (preview only)
    mock_repo.save.assert_not_called()
    mock_repo.get_by_id.assert_called_once_with(ebook_id)

    # Verify page generation was called
    mock_page_service.generate_single_page.assert_called_once()


@pytest.mark.asyncio
async def test_preview_regenerate_page_uses_modal_image_when_provided():
    """Ensure preview regen chains from modal image via workflow_params."""
    ebook_id = 1
    page_index = 1
    modal_image = base64.b64encode(b"MODAL_IMAGE").decode()

    fake_ebook = Ebook(
        id=ebook_id,
        title="Test Coloring Book",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.DRAFT,
        theme_id="dinosaurs",
        audience="6-8",
    )
    fake_ebook.structure_json = {
        "pages_meta": [
            {"page_number": 0, "title": "Cover", "image_data_base64": modal_image},
            {"page_number": 1, "title": "Page 1", "image_data_base64": modal_image},
            {"page_number": 2, "title": "Back", "image_data_base64": modal_image},
        ]
    }

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook

    mock_page_service = AsyncMock()
    mock_page_service.generate_single_page.return_value = b"new_preview"

    use_case = PreviewRegeneratePageUseCase(
        ebook_repository=mock_repo,
        page_service=mock_page_service,
    )

    await use_case.execute(
        ebook_id=ebook_id,
        page_index=page_index,
        current_image_base64=modal_image,
    )

    # Assert workflow_params passed through with modal image hint
    _, kwargs = mock_page_service.generate_single_page.call_args
    assert "workflow_params" in kwargs
    assert kwargs["workflow_params"].get("initial_image_base64") == modal_image


@pytest.mark.asyncio
async def test_preview_regenerate_page_fails_if_ebook_not_found():
    """Test preview regeneration fails if ebook doesn't exist."""
    # Arrange
    ebook_id = 999
    page_index = 1

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = None

    mock_page_service = AsyncMock()

    # Act & Assert
    use_case = PreviewRegeneratePageUseCase(
        ebook_repository=mock_repo,
        page_service=mock_page_service,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(ebook_id=ebook_id, page_index=page_index)

    assert exc_info.value.code == ErrorCode.EBOOK_NOT_FOUND
    assert "not found" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_preview_regenerate_page_fails_if_not_draft():
    """Test preview regeneration fails if ebook is not DRAFT."""
    # Arrange
    ebook_id = 1
    page_index = 1
    fake_ebook = Ebook(
        id=ebook_id,
        title="Test Coloring Book",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.APPROVED,  # Not DRAFT
        theme_id="dinosaurs",
        audience="6-8",
    )

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook

    mock_page_service = AsyncMock()

    # Act & Assert
    use_case = PreviewRegeneratePageUseCase(
        ebook_repository=mock_repo,
        page_service=mock_page_service,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(ebook_id=ebook_id, page_index=page_index)

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "DRAFT" in str(exc_info.value.actionable_hint)


@pytest.mark.asyncio
async def test_preview_regenerate_page_fails_if_invalid_page_index():
    """Test preview regeneration fails with invalid page index."""
    # Arrange
    ebook_id = 1
    invalid_page_index = 10  # Out of bounds
    fake_ebook = Ebook(
        id=ebook_id,
        title="Test Coloring Book",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.DRAFT,
        theme_id="dinosaurs",
        audience="6-8",
    )

    fake_ebook.structure_json = {
        "pages_meta": [
            {"page_number": 0, "title": "Cover"},
            {"page_number": 1, "title": "Page 1"},
            {"page_number": 2, "title": "Back Cover"},
        ]
    }

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook

    mock_page_service = AsyncMock()

    # Act & Assert
    use_case = PreviewRegeneratePageUseCase(
        ebook_repository=mock_repo,
        page_service=mock_page_service,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(ebook_id=ebook_id, page_index=invalid_page_index)

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "Invalid page index" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_preview_regenerate_page_fails_if_no_structure():
    """Test preview regeneration fails if ebook has no structure_json."""
    # Arrange
    ebook_id = 1
    page_index = 1
    fake_ebook = Ebook(
        id=ebook_id,
        title="Test Coloring Book",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.DRAFT,
        theme_id="dinosaurs",
        audience="6-8",
    )
    fake_ebook.structure_json = None  # No structure

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook

    mock_page_service = AsyncMock()

    # Act & Assert
    use_case = PreviewRegeneratePageUseCase(
        ebook_repository=mock_repo,
        page_service=mock_page_service,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(ebook_id=ebook_id, page_index=page_index)

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "structure is missing" in str(exc_info.value.message)
