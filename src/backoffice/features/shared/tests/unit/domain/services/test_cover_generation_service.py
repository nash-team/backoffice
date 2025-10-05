"""Unit tests for CoverGenerationService (V1)."""

import pytest

from backoffice.features.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.domain.cover_generation import CoverGenerationService
from backoffice.features.shared.tests.unit.fakes.fake_cover_port import FakeCoverPort


class TestCoverGenerationService:
    """Tests for CoverGenerationService."""

    def setup_method(self):
        """Setup before each test."""
        # Clear cache before each test
        CoverGenerationService.clear_cache()

    @pytest.mark.asyncio
    async def test_generate_cover_success(self):
        """Test successful cover generation."""
        # Arrange
        fake_port = FakeCoverPort(mode="succeed", image_size=10000)
        service = CoverGenerationService(cover_port=fake_port, enable_cache=True)

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.COLOR,
        )

        # Act
        result = await service.generate_cover(
            prompt="Test cover",
            spec=spec,
            seed=42,
        )

        # Assert
        assert len(result) == 10000
        assert fake_port.call_count == 1
        assert fake_port.last_prompt == "Test cover"
        assert fake_port.last_seed == 42

    @pytest.mark.asyncio
    async def test_generate_cover_uses_cache(self):
        """Test that cache works correctly."""
        # Arrange
        fake_port = FakeCoverPort(mode="succeed", image_size=10000)
        service = CoverGenerationService(cover_port=fake_port, enable_cache=True)

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.COLOR,
        )

        # Act - Generate twice with same prompt and seed
        result1 = await service.generate_cover(prompt="Test", spec=spec, seed=42)
        result2 = await service.generate_cover(prompt="Test", spec=spec, seed=42)

        # Assert - Port called only once
        assert result1 == result2
        assert fake_port.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_cover_cache_miss_different_prompt(self):
        """Test that different prompts don't hit cache."""
        # Arrange
        fake_port = FakeCoverPort(mode="succeed", image_size=10000)
        service = CoverGenerationService(cover_port=fake_port, enable_cache=True)

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.COLOR,
        )

        # Act - Generate with different prompts
        await service.generate_cover(prompt="Test 1", spec=spec, seed=42)
        await service.generate_cover(prompt="Test 2", spec=spec, seed=42)

        # Assert - Port called twice
        assert fake_port.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_cover_quality_validation_fails(self):
        """Test that quality validation catches too-small images."""
        # Arrange
        fake_port = FakeCoverPort(mode="fail_quality")  # Returns tiny image
        service = CoverGenerationService(cover_port=fake_port, enable_cache=False)

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.COLOR,
        )

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await service.generate_cover(prompt="Test", spec=spec, seed=42)

        assert exc_info.value.code == ErrorCode.IMAGE_TOO_SMALL

    @pytest.mark.asyncio
    async def test_generate_cover_provider_unavailable(self):
        """Test error when provider is unavailable."""
        # Arrange
        fake_port = FakeCoverPort(mode="fail_unavailable")
        service = CoverGenerationService(cover_port=fake_port, enable_cache=False)

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.COLOR,
        )

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            await service.generate_cover(prompt="Test", spec=spec, seed=42)

        assert "not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_cover_wrong_color_mode(self):
        """Test validation rejects B&W color mode for covers."""
        # Arrange
        fake_port = FakeCoverPort(mode="succeed")
        service = CoverGenerationService(cover_port=fake_port, enable_cache=False)

        spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            color_mode=ColorMode.BLACK_WHITE,  # Wrong for cover!
        )

        # Act & Assert
        with pytest.raises(DomainError) as exc_info:
            await service.generate_cover(prompt="Test", spec=spec, seed=42)

        assert exc_info.value.code == ErrorCode.WRONG_COLOR_MODE
