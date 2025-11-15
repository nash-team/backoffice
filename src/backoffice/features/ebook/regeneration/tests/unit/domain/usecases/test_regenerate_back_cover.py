"""Tests for RegenerateBackCoverUseCase."""

import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from backoffice.features.ebook.regeneration.domain.usecases.regenerate_back_cover import (
    RegenerateBackCoverUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.shared.infrastructure.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_regenerate_back_cover_success():
    """Test successful back cover regeneration."""
    # Arrange
    ebook_id = 1
    fake_ebook = Ebook(
        id=ebook_id,
        title="Test Coloring Book",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.DRAFT,
        theme_id="dinosaurs",
        audience="6-8",
    )

    # Simulate existing structure with front cover + pages + back cover
    front_cover_bytes = b"fake_front_cover_image"
    old_back_cover_bytes = b"old_back_cover_image"
    page_bytes = b"fake_page_image"

    fake_ebook.structure_json = {
        "pages_meta": [
            {
                "page_number": 0,
                "title": "Cover",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(front_cover_bytes).decode(),
            },
            {
                "page_number": 1,
                "title": "Page 1",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(page_bytes).decode(),
            },
            {
                "page_number": 2,
                "title": "Back Cover",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(old_back_cover_bytes).decode(),
            },
        ]
    }

    # Mock dependencies
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook
    mock_repo.save.return_value = fake_ebook

    mock_cover_service = AsyncMock()
    new_back_cover_bytes = b"new_back_cover_image"
    # Mock the cover_port.remove_text_from_cover method
    mock_cover_service.cover_port.remove_text_from_cover.return_value = new_back_cover_bytes

    mock_assembly_service = AsyncMock()
    mock_file_storage = MagicMock()
    mock_file_storage.is_available.return_value = False  # Skip Drive upload for test

    # Act
    event_bus = EventBus()

    use_case = RegenerateBackCoverUseCase(
        ebook_repository=mock_repo,
        cover_service=mock_cover_service,
        assembly_service=mock_assembly_service,
        file_storage=mock_file_storage,
        event_bus=event_bus,
    )

    result = await use_case.execute(ebook_id=ebook_id)

    # Assert
    assert result.id == ebook_id
    mock_repo.get_by_id.assert_called_once_with(ebook_id)
    mock_cover_service.cover_port.remove_text_from_cover.assert_called_once_with(
        cover_bytes=front_cover_bytes,
        barcode_width_inches=2.0,
        barcode_height_inches=1.2,
        barcode_margin_inches=0.25,
    )

    # Verify structure_json was updated with new back cover
    updated_pages = result.structure_json["pages_meta"]
    assert len(updated_pages) == 3
    assert updated_pages[-1]["title"] == "Back Cover"
    assert updated_pages[-1]["page_number"] == 3  # Last page number

    # Verify new back cover bytes
    new_back_bytes = base64.b64decode(updated_pages[-1]["image_data_base64"])
    assert new_back_bytes == new_back_cover_bytes

    # Verify front cover and content pages unchanged
    assert updated_pages[0]["title"] == "Cover"
    assert updated_pages[1]["title"] == "Page 1"


@pytest.mark.asyncio
async def test_regenerate_back_cover_not_pending():
    """Test that back cover regeneration fails for non-PENDING ebooks."""
    # Arrange
    ebook_id = 1
    fake_ebook = Ebook(
        id=ebook_id,
        title="Test Ebook",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.APPROVED,  # Not DRAFT
    )

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook

    event_bus = EventBus()

    use_case = RegenerateBackCoverUseCase(
        ebook_repository=mock_repo,
        cover_service=AsyncMock(),
        assembly_service=AsyncMock(),
        file_storage=MagicMock(),
        event_bus=event_bus,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Only DRAFT ebooks"):
        await use_case.execute(ebook_id=ebook_id)


@pytest.mark.asyncio
async def test_regenerate_back_cover_missing_structure():
    """Test that back cover regeneration fails when structure is missing."""
    # Arrange
    ebook_id = 1
    fake_ebook = Ebook(
        id=ebook_id,
        title="Test Ebook",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.DRAFT,
        structure_json=None,  # Missing structure
    )

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook

    event_bus = EventBus()

    use_case = RegenerateBackCoverUseCase(
        ebook_repository=mock_repo,
        cover_service=AsyncMock(),
        assembly_service=AsyncMock(),
        file_storage=MagicMock(),
        event_bus=event_bus,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="structure is missing"):
        await use_case.execute(ebook_id=ebook_id)
