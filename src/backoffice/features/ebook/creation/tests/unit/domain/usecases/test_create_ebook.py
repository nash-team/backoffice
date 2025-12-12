"""Unit tests for CreateEbookUseCase (Chicago style with fakes)."""

from datetime import datetime

import pytest

from backoffice.features.ebook.creation.domain.usecases.create_ebook import (
    CreateEbookUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    EbookStatus,
)
from backoffice.features.ebook.shared.domain.entities.generation_request import (
    Audience,
    EbookType,
    GenerationRequest,
    GenerationResult,
    PageMeta,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# === Fakes ===


class FakeEbookRepository:
    """Fake ebook repository for testing."""

    def __init__(self):
        self._ebooks: dict[int, Ebook] = {}
        self._ebook_bytes: dict[int, bytes] = {}
        self._next_id = 1
        self.create_count = 0
        self.save_count = 0
        self.save_bytes_count = 0

    async def create(self, ebook: Ebook) -> Ebook:
        """Create and return ebook with assigned ID."""
        self.create_count += 1
        ebook.id = self._next_id
        self._next_id += 1
        self._ebooks[ebook.id] = ebook
        return ebook

    async def save(self, ebook: Ebook) -> Ebook:
        """Save ebook changes."""
        self.save_count += 1
        self._ebooks[ebook.id] = ebook
        return ebook

    async def save_ebook_bytes(self, ebook_id: int, pdf_bytes: bytes) -> None:
        """Save PDF bytes for ebook."""
        self.save_bytes_count += 1
        self._ebook_bytes[ebook_id] = pdf_bytes

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        return self._ebooks.get(ebook_id)

    def get_saved_bytes(self, ebook_id: int) -> bytes | None:
        """Helper to verify saved bytes."""
        return self._ebook_bytes.get(ebook_id)


class FakeGenerationStrategy:
    """Fake generation strategy for testing."""

    def __init__(
        self,
        should_fail: bool = False,
        pdf_path: str = "/tmp/fake_ebook.pdf",
        page_count: int = 5,
    ):
        self.should_fail = should_fail
        self.pdf_path = pdf_path
        self.page_count = page_count
        self.call_count = 0
        self.last_request: GenerationRequest | None = None

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Fake generation - returns fake result."""
        self.call_count += 1
        self.last_request = request

        if self.should_fail:
            raise Exception("Fake generation failure")

        # Create fake image pages
        pages = []
        for i in range(self.page_count):
            title = "Cover" if i == 0 else f"Page {i}"
            image_data = b"\x89PNG\r\n\x1a\n" + b"x" * 100  # Fake PNG
            pages.append(
                PageMeta(
                    page_number=i,
                    title=title,
                    image_data=image_data,
                    format="PNG",
                    size_bytes=len(image_data),
                    prompt=f"Test prompt {i}",
                )
            )

        return GenerationResult(
            pdf_uri=f"file://{self.pdf_path}",
            pages_meta=pages,
        )


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


# === Fixtures ===


def _create_generation_request(
    title: str = "Test Coloring Book",
    theme: str = "dinosaurs",
    ebook_type: EbookType = EbookType.COLORING,
    audience: Audience = Audience.CHILDREN,
    page_count: int = 5,
) -> GenerationRequest:
    """Create a sample generation request for testing."""
    return GenerationRequest(
        title=title,
        theme=theme,
        ebook_type=ebook_type,
        audience=audience,
        page_count=page_count,
        request_id="test-request-123",
    )


# === Tests ===


class TestCreateEbookUseCase:
    """Test cases for CreateEbookUseCase."""

    @pytest.fixture
    def ebook_repository(self):
        return FakeEbookRepository()

    @pytest.fixture
    def generation_strategy(self):
        return FakeGenerationStrategy()

    @pytest.fixture
    def file_storage(self):
        return FakeFileStorage(mode="succeed")

    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.fixture
    def use_case(self, ebook_repository, generation_strategy, file_storage, event_bus, tmp_path):
        # Create fake PDF file for the strategy
        fake_pdf = tmp_path / "fake_ebook.pdf"
        fake_pdf.write_bytes(b"%PDF-1.7 fake pdf content")
        generation_strategy.pdf_path = str(fake_pdf)

        return CreateEbookUseCase(
            ebook_repository=ebook_repository,
            generation_strategy=generation_strategy,
            event_bus=event_bus,
            file_storage=file_storage,
        )

    async def test_create_ebook_success(self, use_case, ebook_repository, generation_strategy):
        """Test successful ebook creation."""
        # Arrange
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.id is not None
        assert result.title == "Test Coloring Book"
        assert result.status == EbookStatus.DRAFT
        assert result.page_count == 5
        assert generation_strategy.call_count == 1
        assert ebook_repository.create_count == 1

    async def test_create_ebook_with_preview_mode(self, use_case, ebook_repository):
        """Test ebook creation in preview mode."""
        # Arrange
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request, is_preview=True)

        # Assert
        assert result.structure_json is not None
        assert result.structure_json.get("is_preview") is True

    async def test_create_ebook_without_preview_mode(self, use_case, ebook_repository):
        """Test ebook creation without preview mode."""
        # Arrange
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request, is_preview=False)

        # Assert
        assert result.structure_json is not None
        assert result.structure_json.get("is_preview") is False

    async def test_create_ebook_saves_structure_json(self, use_case, ebook_repository, generation_strategy):
        """Test that structure_json contains pages metadata."""
        # Arrange
        request = _create_generation_request()
        generation_strategy.page_count = 3

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.structure_json is not None
        assert "pages_meta" in result.structure_json
        assert len(result.structure_json["pages_meta"]) == 3
        # Check page structure
        first_page = result.structure_json["pages_meta"][0]
        assert first_page["page_number"] == 0
        assert first_page["title"] == "Cover"
        assert "image_data_base64" in first_page
        assert "prompt" in first_page

    async def test_create_ebook_uploads_to_storage(self, use_case, file_storage):
        """Test that ebook is uploaded to storage when available."""
        # Arrange
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request)

        # Assert
        assert file_storage.upload_count == 1
        assert result.drive_id is not None
        assert result.preview_url is not None

    async def test_create_ebook_without_storage(self, ebook_repository, generation_strategy, event_bus, tmp_path):
        """Test ebook creation without file storage."""
        # Arrange
        fake_pdf = tmp_path / "fake_ebook.pdf"
        fake_pdf.write_bytes(b"%PDF-1.7 fake pdf content")
        generation_strategy.pdf_path = str(fake_pdf)

        use_case = CreateEbookUseCase(
            ebook_repository=ebook_repository,
            generation_strategy=generation_strategy,
            event_bus=event_bus,
            file_storage=None,  # No storage
        )
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.id is not None
        assert result.drive_id is None  # No storage upload

    async def test_create_ebook_storage_unavailable(self, ebook_repository, generation_strategy, event_bus, tmp_path):
        """Test ebook creation when storage is unavailable."""
        # Arrange
        fake_pdf = tmp_path / "fake_ebook.pdf"
        fake_pdf.write_bytes(b"%PDF-1.7 fake pdf content")
        generation_strategy.pdf_path = str(fake_pdf)

        file_storage = FakeFileStorage(mode="unavailable")
        use_case = CreateEbookUseCase(
            ebook_repository=ebook_repository,
            generation_strategy=generation_strategy,
            event_bus=event_bus,
            file_storage=file_storage,
        )
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request)

        # Assert - ebook created but no storage upload
        assert result.id is not None
        assert file_storage.upload_count == 0
        assert result.drive_id is None

    async def test_create_ebook_storage_upload_fails(self, ebook_repository, generation_strategy, event_bus, tmp_path):
        """Test ebook creation continues when storage upload fails."""
        # Arrange
        fake_pdf = tmp_path / "fake_ebook.pdf"
        fake_pdf.write_bytes(b"%PDF-1.7 fake pdf content")
        generation_strategy.pdf_path = str(fake_pdf)

        file_storage = FakeFileStorage(mode="fail_upload")
        use_case = CreateEbookUseCase(
            ebook_repository=ebook_repository,
            generation_strategy=generation_strategy,
            event_bus=event_bus,
            file_storage=file_storage,
        )
        request = _create_generation_request()

        # Act - should NOT raise, continues with local storage
        result = await use_case.execute(request)

        # Assert - ebook created despite upload failure
        assert result.id is not None
        assert ebook_repository.create_count == 1

    async def test_create_ebook_saves_pdf_bytes(self, use_case, ebook_repository):
        """Test that PDF bytes are saved to database."""
        # Arrange
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request)

        # Assert
        assert ebook_repository.save_bytes_count == 1
        saved_bytes = ebook_repository.get_saved_bytes(result.id)
        assert saved_bytes is not None
        assert saved_bytes.startswith(b"%PDF")

    async def test_create_ebook_generation_fails(self, ebook_repository, event_bus, tmp_path):
        """Test ebook creation fails when generation fails."""
        # Arrange
        generation_strategy = FakeGenerationStrategy(should_fail=True)
        use_case = CreateEbookUseCase(
            ebook_repository=ebook_repository,
            generation_strategy=generation_strategy,
            event_bus=event_bus,
            file_storage=None,
        )
        request = _create_generation_request()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await use_case.execute(request)

        assert "Fake generation failure" in str(exc_info.value)
        assert ebook_repository.create_count == 0

    async def test_create_ebook_with_different_audience(self, use_case, generation_strategy):
        """Test ebook creation with adult audience."""
        # Arrange
        request = _create_generation_request(audience=Audience.ADULTS)

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.audience == "adults"
        assert generation_strategy.last_request.audience == Audience.ADULTS

    async def test_create_ebook_with_different_theme(self, use_case, generation_strategy):
        """Test ebook creation with different theme."""
        # Arrange
        request = _create_generation_request(theme="unicorns")

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.theme_id == "unicorns"
        assert generation_strategy.last_request.theme == "unicorns"

    async def test_create_ebook_sets_author_as_ai_generated(self, use_case):
        """Test that ebook author is set to 'AI Generated'."""
        # Arrange
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.author == "AI Generated"

    async def test_create_ebook_sets_preview_url_from_generation(self, ebook_repository, generation_strategy, event_bus, tmp_path):
        """Test that preview_url is set from generation result when no storage."""
        # Arrange
        fake_pdf = tmp_path / "my_ebook.pdf"
        fake_pdf.write_bytes(b"%PDF-1.7 fake pdf content")
        generation_strategy.pdf_path = str(fake_pdf)

        use_case = CreateEbookUseCase(
            ebook_repository=ebook_repository,
            generation_strategy=generation_strategy,
            event_bus=event_bus,
            file_storage=None,  # No storage
        )
        request = _create_generation_request()

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.preview_url == f"file://{fake_pdf}"
