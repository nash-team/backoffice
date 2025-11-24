"""Tests for ApplyPageEditUseCase."""

import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from backoffice.features.ebook.regeneration.domain.events.content_page_regenerated_event import (
    ContentPageRegeneratedEvent,
)
from backoffice.features.ebook.regeneration.domain.usecases.apply_page_edit import (
    ApplyPageEditUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.infrastructure.events.event_bus import EventBus
from backoffice.features.shared.infrastructure.events.event_handler import EventHandler


@pytest.mark.asyncio
async def test_apply_page_edit_success():
    """Test successful application of page edit."""
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
    old_page1_bytes = b"old_page_1_image"
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
                "image_data_base64": base64.b64encode(old_page1_bytes).decode(),
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
    mock_repo.save.return_value = fake_ebook

    mock_regeneration_service = AsyncMock()
    mock_regeneration_service.rebuild_and_upload_pdf.return_value = (
        MagicMock(),  # pdf_path
        "http://preview.url",  # preview_url
    )

    # New edited image
    new_page_bytes = b"new_edited_page_image"
    new_page_base64 = base64.b64encode(new_page_bytes).decode("utf-8")

    # Act
    event_bus = EventBus()
    use_case = ApplyPageEditUseCase(
        ebook_repository=mock_repo,
        regeneration_service=mock_regeneration_service,
        event_bus=event_bus,
    )

    result = await use_case.execute(
        ebook_id=ebook_id,
        page_index=page_index,
        image_base64=new_page_base64,
    )

    # Assert
    assert result.id == ebook_id
    assert result.preview_url == "http://preview.url"

    # Verify save was called
    mock_repo.save.assert_called_once()

    # Verify PDF rebuild was called
    mock_regeneration_service.rebuild_and_upload_pdf.assert_called_once()

    # Verify structure_json was updated with new image
    updated_pages = result.structure_json["pages_meta"]
    assert base64.b64decode(updated_pages[page_index]["image_data_base64"]) == new_page_bytes


@pytest.mark.asyncio
async def test_apply_page_edit_fails_if_ebook_not_found():
    """Test apply edit fails if ebook doesn't exist."""
    # Arrange
    ebook_id = 999
    page_index = 1
    image_base64 = base64.b64encode(b"fake_image").decode("utf-8")

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = None

    mock_regeneration_service = AsyncMock()
    event_bus = EventBus()

    # Act & Assert
    use_case = ApplyPageEditUseCase(
        ebook_repository=mock_repo,
        regeneration_service=mock_regeneration_service,
        event_bus=event_bus,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(
            ebook_id=ebook_id,
            page_index=page_index,
            image_base64=image_base64,
        )

    assert exc_info.value.code == ErrorCode.EBOOK_NOT_FOUND
    assert "not found" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_apply_page_edit_fails_if_not_draft():
    """Test apply edit fails if ebook is not DRAFT."""
    # Arrange
    ebook_id = 1
    page_index = 1
    image_base64 = base64.b64encode(b"fake_image").decode("utf-8")

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

    mock_regeneration_service = AsyncMock()
    event_bus = EventBus()

    # Act & Assert
    use_case = ApplyPageEditUseCase(
        ebook_repository=mock_repo,
        regeneration_service=mock_regeneration_service,
        event_bus=event_bus,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(
            ebook_id=ebook_id,
            page_index=page_index,
            image_base64=image_base64,
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "DRAFT" in str(exc_info.value.actionable_hint)


@pytest.mark.asyncio
async def test_apply_page_edit_fails_with_invalid_base64():
    """Test apply edit fails with invalid base64 data."""
    # Arrange
    ebook_id = 1
    page_index = 1
    invalid_base64 = "not-valid-base64!!!"

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
            {"page_number": 1, "title": "Page 1", "image_data_base64": "fake"},
            {"page_number": 2, "title": "Back Cover"},
        ]
    }

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook

    mock_regeneration_service = AsyncMock()
    event_bus = EventBus()

    # Act & Assert
    use_case = ApplyPageEditUseCase(
        ebook_repository=mock_repo,
        regeneration_service=mock_regeneration_service,
        event_bus=event_bus,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(
            ebook_id=ebook_id,
            page_index=page_index,
            image_base64=invalid_base64,
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "base64" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_apply_page_edit_fails_if_invalid_page_index():
    """Test apply edit fails with invalid page index."""
    # Arrange
    ebook_id = 1
    invalid_page_index = 10  # Out of bounds
    image_base64 = base64.b64encode(b"fake_image").decode("utf-8")

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

    mock_regeneration_service = AsyncMock()
    event_bus = EventBus()

    # Act & Assert
    use_case = ApplyPageEditUseCase(
        ebook_repository=mock_repo,
        regeneration_service=mock_regeneration_service,
        event_bus=event_bus,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(
            ebook_id=ebook_id,
            page_index=invalid_page_index,
            image_base64=image_base64,
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "Invalid page index" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_apply_page_edit_emits_domain_event():
    """Test that apply edit emits ContentPageRegeneratedEvent."""
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

    fake_ebook.structure_json = {
        "pages_meta": [
            {"page_number": 0, "title": "Cover", "image_data_base64": "fake"},
            {"page_number": 1, "title": "Page 1", "image_data_base64": "fake"},
            {"page_number": 2, "title": "Back Cover", "image_data_base64": "fake"},
        ]
    }

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = fake_ebook
    mock_repo.save.return_value = fake_ebook

    mock_regeneration_service = AsyncMock()
    mock_regeneration_service.rebuild_and_upload_pdf.return_value = (
        MagicMock(),
        "http://preview.url",
    )

    new_page_base64 = base64.b64encode(b"new_page").decode("utf-8")

    # Act
    event_bus = EventBus()
    use_case = ApplyPageEditUseCase(
        ebook_repository=mock_repo,
        regeneration_service=mock_regeneration_service,
        event_bus=event_bus,
    )

    # Track published events
    published_events = []

    class TrackEventHandler(EventHandler[ContentPageRegeneratedEvent]):
        async def handle(self, event: ContentPageRegeneratedEvent):
            published_events.append(event)

    event_bus.subscribe(ContentPageRegeneratedEvent, TrackEventHandler())

    await use_case.execute(
        ebook_id=ebook_id,
        page_index=page_index,
        image_base64=new_page_base64,
    )

    # Assert
    assert len(published_events) == 1
    assert published_events[0].ebook_id == ebook_id
    assert published_events[0].page_index == page_index
