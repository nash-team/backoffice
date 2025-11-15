"""Unit tests for ExportToKDPInteriorUseCase."""

import base64
from datetime import datetime

import pytest

from backoffice.features.ebook.export.domain.usecases.export_to_kdp_interior import (
    ExportToKDPInteriorUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    EbookConfig,
    EbookStatus,
    KDPExportConfig,
)
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.infrastructure.events.event_bus import EventBus


class FakeEbookRepository:
    """Fake ebook repository for testing."""

    def __init__(self):
        self._ebooks = {}

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        return self._ebooks.get(ebook_id)

    def add_ebook(self, ebook: Ebook) -> None:
        """Helper to add ebook to fake repo."""
        self._ebooks[ebook.id] = ebook


class FakeKDPInteriorAssemblyProvider:
    """Fake KDP interior assembly provider for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.call_count = 0
        self.last_ebook = None
        self.last_config = None

    async def assemble_kdp_interior(self, ebook: Ebook, kdp_config: KDPExportConfig) -> bytes:
        """Fake assembly - returns fake PDF bytes."""
        self.call_count += 1
        self.last_ebook = ebook
        self.last_config = kdp_config

        if self.should_fail:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Assembly failed",
                actionable_hint="Check ebook structure",
            )

        # Return fake PDF bytes
        return b"%PDF-1.7 fake kdp interior content"


class TestExportToKDPInteriorUseCase:
    """Test cases for KDP interior export use case."""

    @pytest.fixture
    def ebook_repository(self):
        """Create fake ebook repository."""
        return FakeEbookRepository()

    @pytest.fixture
    def fake_assembly_provider(self):
        """Create fake KDP interior assembly provider."""
        return FakeKDPInteriorAssemblyProvider()

    @pytest.fixture
    def event_bus(self):
        """Create event bus."""
        return EventBus()

    @pytest.fixture
    def use_case(self, ebook_repository, event_bus, fake_assembly_provider):
        """Create use case with dependencies."""
        return ExportToKDPInteriorUseCase(
            ebook_repository=ebook_repository,
            event_bus=event_bus,
            kdp_interior_assembly_provider=fake_assembly_provider,
        )

    @pytest.fixture
    def sample_ebook_with_structure(self):
        """Create sample ebook with valid structure."""
        # Create a fake page (1x1 transparent PNG)
        fake_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        fake_b64 = base64.b64encode(fake_png).decode("utf-8")

        return Ebook(
            id=1,
            title="Test Coloring Book",
            author="Test Author",
            created_at=datetime.now(),
            status=EbookStatus.APPROVED,
            config=EbookConfig(ebook_type="coloring_book", number_of_pages=25),
            page_count=27,  # cover + 25 content + back cover
            structure_json={
                "pages_meta": [
                    {
                        "page_number": 0,
                        "title": "Cover",
                        "image_data_base64": fake_b64,
                    },
                    *[
                        {
                            "page_number": i,
                            "title": f"Page {i}",
                            "image_data_base64": fake_b64,
                        }
                        for i in range(1, 26)
                    ],
                    {
                        "page_number": 26,
                        "title": "Back Cover",
                        "image_data_base64": fake_b64,
                    },
                ]
            },
        )

    async def test_export_approved_ebook_success(
        self,
        use_case,
        ebook_repository,
        sample_ebook_with_structure,
        fake_assembly_provider,
    ):
        """Test exporting APPROVED ebook to KDP interior format."""
        # Arrange
        ebook_repository.add_ebook(sample_ebook_with_structure)

        # Act
        pdf_bytes = await use_case.execute(ebook_id=1, preview_mode=False)

        # Assert
        assert pdf_bytes == b"%PDF-1.7 fake kdp interior content"
        assert fake_assembly_provider.call_count == 1
        assert fake_assembly_provider.last_ebook == sample_ebook_with_structure

    async def test_export_draft_in_preview_mode_success(
        self,
        use_case,
        ebook_repository,
        sample_ebook_with_structure,
        fake_assembly_provider,
    ):
        """Test exporting DRAFT ebook in preview mode (allowed)."""
        # Arrange
        sample_ebook_with_structure.status = EbookStatus.DRAFT
        ebook_repository.add_ebook(sample_ebook_with_structure)

        # Act
        pdf_bytes = await use_case.execute(ebook_id=1, preview_mode=True)

        # Assert
        assert pdf_bytes == b"%PDF-1.7 fake kdp interior content"
        assert fake_assembly_provider.call_count == 1

    async def test_export_draft_without_preview_fails(
        self, use_case, ebook_repository, sample_ebook_with_structure
    ):
        """Test exporting DRAFT ebook for download fails (not allowed)."""
        # Arrange
        sample_ebook_with_structure.status = EbookStatus.DRAFT
        ebook_repository.add_ebook(sample_ebook_with_structure)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1, preview_mode=False)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "APPROVED" in str(exc_info.value)

    async def test_export_nonexistent_ebook_fails(self, use_case):
        """Test exporting nonexistent ebook raises error."""
        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=999)

        assert exc_info.value.code == ErrorCode.EBOOK_NOT_FOUND

    async def test_export_ebook_without_page_count_fails(
        self, use_case, ebook_repository, sample_ebook_with_structure
    ):
        """Test exporting ebook without page_count fails."""
        # Arrange
        sample_ebook_with_structure.page_count = None
        ebook_repository.add_ebook(sample_ebook_with_structure)

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await use_case.execute(ebook_id=1)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "page_count" in str(exc_info.value)

    async def test_export_uses_custom_kdp_config(
        self,
        use_case,
        ebook_repository,
        sample_ebook_with_structure,
        fake_assembly_provider,
    ):
        """Test export uses custom KDP config when provided."""
        # Arrange
        ebook_repository.add_ebook(sample_ebook_with_structure)
        custom_config = KDPExportConfig(
            trim_size=(6.0, 9.0),  # Different from default 8x10
            paper_type="standard_color",
        )

        # Act
        await use_case.execute(ebook_id=1, kdp_config=custom_config)

        # Assert
        assert fake_assembly_provider.last_config.trim_size == (6.0, 9.0)
        assert fake_assembly_provider.last_config.paper_type == "standard_color"
