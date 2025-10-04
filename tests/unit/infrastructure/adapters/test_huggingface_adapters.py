"""Unit tests for Hugging Face image provider."""

import base64
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from backoffice.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.infrastructure.providers.huggingface_image_provider import (
    HuggingFaceImageProvider,
)


class TestHuggingFaceImageProvider:
    """Tests for Hugging Face image generation provider."""

    @pytest.fixture
    def mock_hf_client(self):
        """Mock Hugging Face InferenceClient for testing."""
        mock_client = MagicMock()

        # Mock successful text_to_image response (returns PIL Image)
        fake_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        fake_png = base64.b64decode(fake_png_b64)

        # Create PIL Image from bytes
        from io import BytesIO

        pil_image = Image.open(BytesIO(fake_png))
        mock_client.text_to_image.return_value = pil_image

        return mock_client

    @pytest.mark.asyncio
    async def test_generate_cover_success(self, mock_hf_client):
        """Test successful cover generation with FLUX.1-schnell."""
        # Arrange
        provider = HuggingFaceImageProvider(model="black-forest-labs/FLUX.1-schnell")
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Mock the client
        provider.client = mock_hf_client

        # Act
        result = await provider.generate_cover(
            prompt="A colorful dinosaur cover", spec=spec, seed=42
        )

        # Assert
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify API was called with correct parameters
        mock_hf_client.text_to_image.assert_called_once()
        call_args = mock_hf_client.text_to_image.call_args

        # Check parameters
        input_params = call_args[1]
        assert "A colorful dinosaur cover" in input_params["prompt"]
        assert input_params["model"] == "black-forest-labs/FLUX.1-schnell"
        assert input_params["guidance_scale"] == 7.5
        assert input_params["num_inference_steps"] == 8  # With seed (FLUX.1-schnell optimized)

    @pytest.mark.asyncio
    async def test_generate_cover_with_bw_color_mode(self, mock_hf_client):
        """Test cover generation with black & white color mode for coloring pages."""
        # Arrange
        provider = HuggingFaceImageProvider()
        provider.client = mock_hf_client
        spec = ImageSpec(
            width_px=1024, height_px=1024, format="png", color_mode=ColorMode.BLACK_WHITE
        )

        # Act
        result = await provider.generate_cover(prompt="Dinosaur coloring page", spec=spec, seed=123)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

        # Verify prompt includes B&W instructions
        call_args = mock_hf_client.text_to_image.call_args
        input_params = call_args[1]
        prompt_content = input_params["prompt"].lower()
        assert "black and white" in prompt_content
        assert "line art" in prompt_content

    @pytest.mark.asyncio
    async def test_generate_cover_tracks_usage(self, mock_hf_client):
        """Test that cover generation tracks usage and cost (FREE)."""
        # Arrange
        mock_tracker = AsyncMock()
        provider = HuggingFaceImageProvider(token_tracker=mock_tracker)
        provider.client = mock_hf_client
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Act
        await provider.generate_cover(prompt="Test", spec=spec)

        # Assert
        mock_tracker.add_usage_metrics.assert_called_once()
        usage_metrics = mock_tracker.add_usage_metrics.call_args[0][0]

        # Verify cost tracking (FREE)
        assert usage_metrics.model == "black-forest-labs/FLUX.1-schnell"
        assert usage_metrics.cost == Decimal("0")  # FREE!
        assert usage_metrics.prompt_tokens == 0  # HF doesn't expose tokens
        assert usage_metrics.completion_tokens == 0

    @pytest.mark.asyncio
    async def test_generate_cover_without_seed(self, mock_hf_client):
        """Test cover generation without seed (randomized)."""
        # Arrange
        provider = HuggingFaceImageProvider()
        provider.client = mock_hf_client
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Act
        result = await provider.generate_cover(prompt="Test", spec=spec, seed=None)

        # Assert
        assert result is not None

        # Verify num_inference_steps reduced for faster generation
        call_args = mock_hf_client.text_to_image.call_args
        input_params = call_args[1]
        assert (
            input_params["num_inference_steps"] == 4
        )  # Without seed: faster (FLUX.1-schnell optimized)

    @pytest.mark.asyncio
    async def test_generate_cover_handles_exceptions(self, mock_hf_client):
        """Test that cover generation handles API exceptions gracefully."""
        # Arrange
        provider = HuggingFaceImageProvider()
        provider.client = mock_hf_client
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Mock exception
        mock_hf_client.text_to_image.side_effect = Exception("API rate limit exceeded")

        # Act & Assert
        from backoffice.domain.errors.error_taxonomy import DomainError

        with pytest.raises(DomainError) as exc_info:
            await provider.generate_cover(prompt="Test", spec=spec)

        # Verify error details
        assert "Hugging Face generation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_cover_not_available_without_token(self):
        """Test that cover generation fails if HF_API_TOKEN not configured."""
        # Arrange
        with patch.dict("os.environ", {}, clear=True):
            provider = HuggingFaceImageProvider()

        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Act & Assert
        from backoffice.domain.errors.error_taxonomy import DomainError

        with pytest.raises(DomainError) as exc_info:
            await provider.generate_cover(prompt="Test", spec=spec)

        # Verify error message
        assert "Hugging Face provider not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_page_delegates_to_generate_cover(self, mock_hf_client):
        """Test that generate_page delegates to generate_cover."""
        # Arrange
        provider = HuggingFaceImageProvider()
        provider.client = mock_hf_client
        spec = ImageSpec(
            width_px=1024, height_px=1024, format="png", color_mode=ColorMode.BLACK_WHITE
        )

        # Act
        result = await provider.generate_page(prompt="Dinosaur page", spec=spec, seed=42)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

        # Verify same parameters as generate_cover
        mock_hf_client.text_to_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_text_from_cover_adds_barcode_space(self, mock_hf_client):
        """Test successful barcode space addition (PIL-based fallback)."""
        # Arrange
        provider = HuggingFaceImageProvider()
        provider.client = mock_hf_client

        # Use valid PNG bytes
        fake_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        cover_bytes = base64.b64decode(fake_png_b64)

        # Act
        result = await provider.remove_text_from_cover(cover_bytes=cover_bytes)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)
        # PIL fallback adds barcode space, no HF API call
        mock_hf_client.text_to_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_text_tracks_usage(self, mock_hf_client):
        """Test that text removal tracks usage (FREE)."""
        # Arrange
        mock_tracker = AsyncMock()
        provider = HuggingFaceImageProvider(token_tracker=mock_tracker)
        provider.client = mock_hf_client

        # Use valid PNG bytes
        fake_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        cover_bytes = base64.b64decode(fake_png_b64)

        # Act
        await provider.remove_text_from_cover(cover_bytes=cover_bytes)

        # Assert
        mock_tracker.add_usage_metrics.assert_called_once()
        usage_metrics = mock_tracker.add_usage_metrics.call_args[0][0]

        # Verify cost tracking (FREE)
        assert "text-removal" in usage_metrics.model
        assert usage_metrics.cost == Decimal("0")  # FREE!

    def test_provider_initializes_with_correct_model(self):
        """Test that provider stores the correct model."""
        # Arrange & Act
        provider = HuggingFaceImageProvider(model="custom/flux-model")

        # Assert
        assert provider.model == "custom/flux-model"

    def test_provider_uses_default_model(self):
        """Test that provider uses FLUX.1-schnell as default."""
        # Arrange & Act
        provider = HuggingFaceImageProvider()

        # Assert
        assert provider.model == "black-forest-labs/FLUX.1-schnell"

    def test_provider_uses_api_token_from_environment(self):
        """Test that provider loads API token from environment."""
        # Arrange & Act
        with patch.dict("os.environ", {"HF_API_TOKEN": "test-token"}):
            with patch("huggingface_hub.InferenceClient"):
                provider = HuggingFaceImageProvider()

        # Assert - client should be initialized (not None)
        assert provider.client is not None

    def test_provider_unavailable_without_token(self):
        """Test that provider is unavailable without API token."""
        # Arrange & Act
        with patch.dict("os.environ", {}, clear=True):
            provider = HuggingFaceImageProvider()

        # Assert
        assert provider.is_available() is False

    def test_provider_does_not_support_vectorization(self):
        """Test that Hugging Face provider doesn't support SVG vectorization."""
        # Arrange & Act
        provider = HuggingFaceImageProvider()

        # Assert
        assert provider.supports_vectorization() is False

    @pytest.mark.asyncio
    async def test_add_rounded_border_to_bw_image(self, mock_hf_client):
        """Test that B&W coloring pages get rounded borders."""
        # Arrange
        provider = HuggingFaceImageProvider()
        provider.client = mock_hf_client
        spec = ImageSpec(
            width_px=512, height_px=512, format="png", color_mode=ColorMode.BLACK_WHITE
        )

        # Act
        result = await provider.generate_cover(prompt="Test coloring page", spec=spec)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

        # Verify border was added (result should be larger than original 1x1 PNG)
        assert len(result) > 100  # Border adds pixels
