"""Unit tests for ContentPageGenerationService (V1)."""

import pytest

from backoffice.features.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.domain.page_generation import ContentPageGenerationService
from backoffice.features.shared.tests.unit.fakes.fake_page_port import FakePagePort


class TestContentPageGenerationService:
    """Tests for ContentPageGenerationService."""

    def setup_method(self):
        """Setup before each test."""
        # Clear cache before each test
        ContentPageGenerationService.clear_cache()

    @pytest.mark.asyncio
    async def test_generate_pages_success(self):
        """Test successful batch page generation."""
        # Arrange
        fake_port = FakePagePort(mode="succeed", image_size=8000)
        service = ContentPageGenerationService(
            page_port=fake_port,
            max_concurrent=3,
            enable_cache=True,
        )

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.BLACK_WHITE,
        )

        prompts = ["Page 1", "Page 2", "Page 3"]

        # Act
        results = await service.generate_pages(
            prompts=prompts,
            spec=spec,
            seed=42,
        )

        # Assert
        assert len(results) == 3
        assert fake_port.call_count == 3
        assert all(len(page) > 8000 for page in results)  # Each page has unique suffix

    @pytest.mark.asyncio
    async def test_generate_pages_uses_cache(self):
        """Test that cache works when generating twice."""
        # Arrange
        fake_port = FakePagePort(mode="succeed", image_size=8000)
        service = ContentPageGenerationService(
            page_port=fake_port,
            max_concurrent=3,
            enable_cache=True,
        )

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.BLACK_WHITE,
        )

        # Same prompt with same seed
        prompts = ["Page 1"]

        # Act - Generate twice
        results1 = await service.generate_pages(
            prompts=prompts,
            spec=spec,
            seed=42,
        )
        results2 = await service.generate_pages(
            prompts=prompts,
            spec=spec,
            seed=42,
        )

        # Assert - Only 1 call (second generation hit cache)
        assert len(results1) == 1
        assert len(results2) == 1
        assert fake_port.call_count == 1
        assert results1[0] == results2[0]  # Same data from cache

    @pytest.mark.asyncio
    async def test_generate_pages_concurrency_control(self):
        """Test that semaphore limits concurrent calls."""
        # Arrange
        fake_port = FakePagePort(mode="succeed", image_size=8000)
        service = ContentPageGenerationService(
            page_port=fake_port,
            max_concurrent=2,  # Limit to 2 concurrent
            enable_cache=False,  # Disable cache for this test
        )

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.BLACK_WHITE,
        )

        # Generate 5 pages
        prompts = [f"Page {i}" for i in range(5)]

        # Act
        results = await service.generate_pages(
            prompts=prompts,
            spec=spec,
            seed=42,
        )

        # Assert
        assert len(results) == 5
        assert fake_port.call_count == 5

    @pytest.mark.asyncio
    async def test_generate_pages_quality_validation_fails(self):
        """Test that quality validation catches too-small images."""
        # Arrange
        fake_port = FakePagePort(mode="fail_quality")  # Returns tiny images
        service = ContentPageGenerationService(
            page_port=fake_port,
            max_concurrent=3,
            enable_cache=False,
        )

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.BLACK_WHITE,
        )

        prompts = ["Page 1"]

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await service.generate_pages(prompts=prompts, spec=spec, seed=42)

        assert exc_info.value.code == ErrorCode.IMAGE_TOO_SMALL

    @pytest.mark.asyncio
    async def test_generate_pages_provider_unavailable(self):
        """Test error when provider is unavailable."""
        # Arrange
        fake_port = FakePagePort(mode="fail_unavailable")
        service = ContentPageGenerationService(
            page_port=fake_port,
            max_concurrent=3,
            enable_cache=False,
        )

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.BLACK_WHITE,
        )

        prompts = ["Page 1"]

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            await service.generate_pages(prompts=prompts, spec=spec, seed=42)

        assert "not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_pages_empty_list(self):
        """Test generating zero pages."""
        # Arrange
        fake_port = FakePagePort(mode="succeed")
        service = ContentPageGenerationService(
            page_port=fake_port,
            max_concurrent=3,
            enable_cache=False,
        )

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.BLACK_WHITE,
        )

        # Act
        results = await service.generate_pages(prompts=[], spec=spec, seed=42)

        # Assert
        assert len(results) == 0
        assert fake_port.call_count == 0
