"""Unit tests for ExportToKDPUseCase (Chicago style with fakes)."""

import base64
from datetime import datetime

import pytest

from backoffice.features.ebook.export.domain.usecases.export_to_kdp import (
    ExportToKDPUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    EbookConfig,
    EbookStatus,
    KDPExportConfig,
)
from backoffice.features.ebook.shared.domain.entities.theme_profile import BackCoverConfig, ThemeProfile
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# === Fakes ===


class FakeEbookRepository:
    """Fake ebook repository for testing."""

    def __init__(self):
        self._ebooks: dict[int, Ebook] = {}

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        return self._ebooks.get(ebook_id)

    def add_ebook(self, ebook: Ebook) -> None:
        """Helper to add ebook to fake repo."""
        self._ebooks[ebook.id] = ebook


class FakeKDPAssemblyProvider:
    """Fake KDP assembly provider for testing."""

    def __init__(self, should_fail: bool = False, pdf_size: int = 50000):
        self.should_fail = should_fail
        self.pdf_size = pdf_size
        self.call_count = 0
        self.last_ebook = None
        self.last_config = None
        self.last_front_cover_bytes = None
        self.last_back_cover_bytes = None

    async def assemble_kdp_paperback(
        self,
        ebook: Ebook,
        back_cover_bytes: bytes,
        front_cover_bytes: bytes,
        kdp_config: KDPExportConfig,
        isbn: str | None = None,
        spine_colors: list | None = None,
    ) -> bytes:
        """Fake assembly - returns fake PDF bytes."""
        self.call_count += 1
        self.last_ebook = ebook
        self.last_config = kdp_config
        self.last_front_cover_bytes = front_cover_bytes
        self.last_back_cover_bytes = back_cover_bytes
        self.last_isbn = isbn
        self.last_spine_colors = spine_colors

        if self.should_fail:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="KDP assembly failed",
                actionable_hint="Check ebook covers",
            )

        # Return fake PDF bytes
        return b"%PDF-1.7 fake kdp cover content" + b"x" * self.pdf_size


class FakeImageProvider:
    """Fake image provider for testing."""

    def __init__(self):
        self.call_count = 0

    async def remove_text_from_image(self, image_bytes: bytes) -> bytes:
        self.call_count += 1
        return image_bytes  # Return same image


class FakeThemeRepository:
    """Fake theme repository for testing ISBN lookup."""

    def __init__(self, themes: dict[str, ThemeProfile] | None = None):
        self._themes = themes or {}

    def get_theme_by_id(self, theme_id: str) -> ThemeProfile:
        if theme_id not in self._themes:
            raise ValueError(f"Theme '{theme_id}' not found")
        return self._themes[theme_id]


def _make_theme_profile(theme_id: str = "dinosaurs", isbn: str | None = None) -> ThemeProfile:
    """Create a minimal ThemeProfile for testing."""
    from backoffice.features.ebook.shared.domain.entities.theme_profile import Palette, PromptBlocks

    back_cover = BackCoverConfig(
        preview_pages=[0, 1],
        tagline="Test tagline",
        description="Test description",
        author="Test Author",
        publisher="Test Publisher",
        isbn=isbn,
    )
    return ThemeProfile(
        id=theme_id,
        label="Dinosaurs",
        palette=Palette(base=["#FF0000"], accents_allowed=[], forbidden_keywords=[]),
        blocks=PromptBlocks(subject="dinos", environment="forest", tone="fun", positives=["cute"], negatives=["scary"]),
        cover_title_image="config/branding/themes/assets/title.png",
        cover_footer_image="config/branding/themes/assets/footer.png",
        back_cover=back_cover,
    )


# === Fixtures ===


def _create_fake_png() -> bytes:
    """Create a minimal valid PNG for testing."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _create_sample_ebook(
    ebook_id: int = 1,
    status: EbookStatus = EbookStatus.APPROVED,
    page_count: int = 27,
    with_structure: bool = True,
) -> Ebook:
    """Create a sample ebook for testing."""
    fake_b64 = base64.b64encode(_create_fake_png()).decode("utf-8")

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


class TestExportToKDPUseCase:
    """Test cases for ExportToKDPUseCase."""

    @pytest.fixture
    def ebook_repository(self):
        return FakeEbookRepository()

    @pytest.fixture
    def fake_kdp_provider(self):
        return FakeKDPAssemblyProvider()

    @pytest.fixture
    def fake_image_provider(self):
        return FakeImageProvider()

    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.fixture
    def use_case(self, ebook_repository, event_bus, fake_kdp_provider, fake_image_provider):
        return ExportToKDPUseCase(
            ebook_repository=ebook_repository,
            event_bus=event_bus,
            image_provider=fake_image_provider,
            kdp_assembly_provider=fake_kdp_provider,
        )

    async def test_export_approved_ebook_success(self, use_case, ebook_repository, fake_kdp_provider):
        """Test exporting APPROVED ebook to KDP format."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)
        ebook_repository.add_ebook(ebook)

        # Act
        pdf_bytes = await use_case.execute(ebook_id=1)

        # Assert
        assert pdf_bytes.startswith(b"%PDF")
        assert fake_kdp_provider.call_count == 1
        assert fake_kdp_provider.last_ebook == ebook

    async def test_export_draft_in_preview_mode_success(self, use_case, ebook_repository, fake_kdp_provider):
        """Test exporting DRAFT ebook in preview mode (allowed)."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT)
        ebook_repository.add_ebook(ebook)

        # Act
        pdf_bytes = await use_case.execute(ebook_id=1, preview_mode=True)

        # Assert
        assert pdf_bytes.startswith(b"%PDF")
        assert fake_kdp_provider.call_count == 1

    async def test_export_draft_without_preview_fails(self, use_case, ebook_repository):
        """Test exporting DRAFT ebook for download fails."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT)
        ebook_repository.add_ebook(ebook)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1, preview_mode=False)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "APPROVED" in str(exc_info.value.message)

    async def test_export_rejected_ebook_fails(self, use_case, ebook_repository):
        """Test exporting REJECTED ebook fails even in preview mode."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.REJECTED)
        ebook_repository.add_ebook(ebook)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1, preview_mode=True)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    async def test_export_nonexistent_ebook_fails(self, use_case):
        """Test exporting nonexistent ebook raises error."""
        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=999)

        assert exc_info.value.code == ErrorCode.EBOOK_NOT_FOUND

    async def test_export_ebook_without_page_count_fails(self, use_case, ebook_repository):
        """Test exporting ebook without page_count fails."""
        # Arrange
        ebook = _create_sample_ebook()
        ebook.page_count = None
        ebook_repository.add_ebook(ebook)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "page_count" in str(exc_info.value.message)

    async def test_export_ebook_without_structure_fails(self, use_case, ebook_repository):
        """Test exporting ebook without structure fails."""
        # Arrange
        ebook = _create_sample_ebook(with_structure=False)
        ebook_repository.add_ebook(ebook)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    async def test_export_uses_custom_kdp_config(self, use_case, ebook_repository, fake_kdp_provider):
        """Test export uses custom KDP config."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)
        ebook_repository.add_ebook(ebook)
        custom_config = KDPExportConfig(
            trim_size=(6.0, 9.0),
            paper_type="standard_color",
        )

        # Act
        await use_case.execute(ebook_id=1, kdp_config=custom_config)

        # Assert
        assert fake_kdp_provider.last_config.trim_size == (6.0, 9.0)
        assert fake_kdp_provider.last_config.paper_type == "standard_color"

    async def test_export_short_book_adjusts_paper_type(self, use_case, ebook_repository, fake_kdp_provider):
        """Test that short books (< 24 pages) get paper type adjusted."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED, page_count=20)
        ebook_repository.add_ebook(ebook)

        # Act
        await use_case.execute(ebook_id=1)

        # Assert - paper type should be adjusted from premium_color to standard_color
        assert fake_kdp_provider.last_config.paper_type == "standard_color"

    async def test_export_extracts_front_and_back_cover(self, use_case, ebook_repository, fake_kdp_provider):
        """Test that export extracts both covers from structure."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)
        ebook_repository.add_ebook(ebook)

        # Act
        await use_case.execute(ebook_id=1)

        # Assert
        assert fake_kdp_provider.last_front_cover_bytes is not None
        assert fake_kdp_provider.last_back_cover_bytes is not None
        # Both should be valid PNG bytes
        assert fake_kdp_provider.last_front_cover_bytes.startswith(b"\x89PNG")
        assert fake_kdp_provider.last_back_cover_bytes.startswith(b"\x89PNG")

    async def test_export_ebook_with_only_one_page_fails(self, use_case, ebook_repository):
        """Test that ebook with only one page (no back cover) fails."""
        # Arrange
        fake_b64 = base64.b64encode(_create_fake_png()).decode("utf-8")
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)
        ebook.structure_json = {"pages_meta": [{"page_number": 0, "title": "Cover", "image_data_base64": fake_b64}]}
        ebook_repository.add_ebook(ebook)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "at least 2 pages" in str(exc_info.value.message)

    async def test_export_passes_isbn_from_theme_to_assembly(self, ebook_repository, event_bus, fake_image_provider):
        """Test that ISBN from theme config is passed to KDP assembly provider."""
        # Arrange
        fake_kdp = FakeKDPAssemblyProvider()
        theme = _make_theme_profile(theme_id="dinosaurs", isbn="9781234567897")
        fake_theme_repo = FakeThemeRepository(themes={"dinosaurs": theme})
        use_case = ExportToKDPUseCase(
            ebook_repository=ebook_repository,
            event_bus=event_bus,
            image_provider=fake_image_provider,
            kdp_assembly_provider=fake_kdp,
            theme_repository=fake_theme_repo,
        )
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)
        ebook.theme_id = "dinosaurs"
        ebook_repository.add_ebook(ebook)

        # Act
        await use_case.execute(ebook_id=1)

        # Assert
        assert fake_kdp.last_isbn == "9781234567897"

    async def test_export_no_isbn_when_theme_has_no_isbn(self, ebook_repository, event_bus, fake_image_provider):
        """Test that ISBN is None when theme has no ISBN configured."""
        # Arrange
        fake_kdp = FakeKDPAssemblyProvider()
        theme = _make_theme_profile(theme_id="dinosaurs", isbn=None)
        fake_theme_repo = FakeThemeRepository(themes={"dinosaurs": theme})
        use_case = ExportToKDPUseCase(
            ebook_repository=ebook_repository,
            event_bus=event_bus,
            image_provider=fake_image_provider,
            kdp_assembly_provider=fake_kdp,
            theme_repository=fake_theme_repo,
        )
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)
        ebook.theme_id = "dinosaurs"
        ebook_repository.add_ebook(ebook)

        # Act
        await use_case.execute(ebook_id=1)

        # Assert
        assert fake_kdp.last_isbn is None

    async def test_export_no_isbn_when_no_theme_id(self, use_case, ebook_repository, fake_kdp_provider):
        """Test that ISBN is None when ebook has no theme_id."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)
        ebook.theme_id = None
        ebook_repository.add_ebook(ebook)

        # Act
        await use_case.execute(ebook_id=1)

        # Assert
        assert fake_kdp_provider.last_isbn is None
