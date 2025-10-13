"""Unit tests for ColoringBookStrategy (V1)."""

from pathlib import Path

import pytest

from backoffice.features.ebook.creation.domain.strategies.coloring_book_strategy import (
    ColoringBookStrategy,
)
from backoffice.features.ebook.shared.domain.services.cover_generation import CoverGenerationService
from backoffice.features.ebook.shared.domain.services.page_generation import (
    ContentPageGenerationService,
)
from backoffice.features.ebook.shared.domain.services.pdf_assembly import PDFAssemblyService
from backoffice.features.shared.domain.entities.generation_request import (
    AgeGroup,
    EbookType,
    GenerationRequest,
)
from backoffice.features.shared.tests.unit.fakes.fake_assembly_port import FakeAssemblyPort
from backoffice.features.shared.tests.unit.fakes.fake_cover_port import FakeCoverPort
from backoffice.features.shared.tests.unit.fakes.fake_page_port import FakePagePort


class TestColoringBookStrategy:
    """Tests for ColoringBookStrategy."""

    def setup_method(self):
        """Setup before each test."""
        # Clear caches
        CoverGenerationService.clear_cache()
        ContentPageGenerationService.clear_cache()

    @pytest.mark.asyncio
    async def test_generate_coloring_book_success(self):
        """Test successful coloring book generation."""
        # Arrange
        fake_cover_port = FakeCoverPort(mode="succeed", image_size=10000)
        fake_page_port = FakePagePort(mode="succeed", image_size=8000)
        fake_assembly_port = FakeAssemblyPort(mode="succeed")

        cover_service = CoverGenerationService(cover_port=fake_cover_port, enable_cache=False)
        pages_service = ContentPageGenerationService(
            page_port=fake_page_port,
            max_concurrent=3,
            enable_cache=False,
        )
        assembly_service = PDFAssemblyService(assembly_port=fake_assembly_port)

        strategy = ColoringBookStrategy(
            cover_service=cover_service,
            pages_service=pages_service,
            assembly_service=assembly_service,
        )

        request = GenerationRequest(
            title="Test Book",
            theme="Animals",
            age_group=AgeGroup.PRESCHOOL,
            ebook_type=EbookType.COLORING,
            page_count=24,
            request_id="test-123",
            seed=42,
        )

        # Act
        result = await strategy.generate(request)

        # Assert
        assert result.pdf_uri.startswith("file://")
        assert len(result.pages_meta) == 26  # 1 cover + 24 pages + 1 back cover
        assert result.pages_meta[0].title == "Cover"
        assert result.pages_meta[1].title == "Page 1"
        assert fake_cover_port.call_count == 1
        assert fake_page_port.call_count == 24
        assert fake_assembly_port.call_count == 1

        # Verify PDF was created
        pdf_path = result.pdf_uri.replace("file://", "")
        assert Path(pdf_path).exists()

    @pytest.mark.asyncio
    async def test_generate_coloring_book_single_page(self):
        """Test generating coloring book with just 1 page."""
        # Arrange
        fake_cover_port = FakeCoverPort(mode="succeed")
        fake_page_port = FakePagePort(mode="succeed")
        fake_assembly_port = FakeAssemblyPort(mode="succeed")

        cover_service = CoverGenerationService(cover_port=fake_cover_port, enable_cache=False)
        pages_service = ContentPageGenerationService(
            page_port=fake_page_port,
            max_concurrent=3,
            enable_cache=False,
        )
        assembly_service = PDFAssemblyService(assembly_port=fake_assembly_port)

        strategy = ColoringBookStrategy(
            cover_service=cover_service,
            pages_service=pages_service,
            assembly_service=assembly_service,
        )

        request = GenerationRequest(
            title="Test Book",
            theme="Animals",
            age_group=AgeGroup.PRESCHOOL,
            ebook_type=EbookType.COLORING,
            page_count=24,  # KDP minimum
            request_id="test-456",
            seed=42,
        )

        # Act
        result = await strategy.generate(request)

        # Assert
        assert len(result.pages_meta) == 26  # 1 cover + 24 pages + 1 back cover
        assert fake_cover_port.call_count == 1
        assert fake_page_port.call_count == 24

    @pytest.mark.asyncio
    async def test_generate_coloring_book_metadata_correctness(self):
        """Test that page metadata is correct."""
        # Arrange
        fake_cover_port = FakeCoverPort(mode="succeed", image_size=12000)
        fake_page_port = FakePagePort(mode="succeed", image_size=9000)
        fake_assembly_port = FakeAssemblyPort(mode="succeed")

        cover_service = CoverGenerationService(cover_port=fake_cover_port, enable_cache=False)
        pages_service = ContentPageGenerationService(
            page_port=fake_page_port,
            max_concurrent=3,
            enable_cache=False,
        )
        assembly_service = PDFAssemblyService(assembly_port=fake_assembly_port)

        strategy = ColoringBookStrategy(
            cover_service=cover_service,
            pages_service=pages_service,
            assembly_service=assembly_service,
        )

        request = GenerationRequest(
            title="Test Book",
            theme="Animals",
            age_group=AgeGroup.PRESCHOOL,
            ebook_type=EbookType.COLORING,
            page_count=24,
            request_id="test-789",
            seed=42,
        )

        # Act
        result = await strategy.generate(request)

        # Assert metadata
        assert result.pages_meta[0].page_number == 0
        assert result.pages_meta[0].title == "Cover"
        assert result.pages_meta[0].format == "PNG"
        assert result.pages_meta[0].size_bytes == 12000

        assert result.pages_meta[1].page_number == 1
        assert result.pages_meta[1].title == "Page 1"
        assert result.pages_meta[1].size_bytes > 9000  # Includes unique suffix

        assert result.pages_meta[2].page_number == 2
        assert result.pages_meta[2].title == "Page 2"
