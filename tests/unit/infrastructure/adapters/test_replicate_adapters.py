"""Unit tests for Replicate image provider."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from backoffice.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.infrastructure.providers.replicate_image_provider import (
    ReplicateImageProvider,
)


class TestReplicateImageProvider:
    """Tests for Replicate image generation adapter."""

    @pytest.fixture
    def mock_replicate_client(self):
        """Mock Replicate client for testing."""
        import base64

        mock_client = MagicMock()

        # Mock successful flux-schnell response (returns list of FileOutput)
        mock_file_output = MagicMock()
        # Fake 1x1 transparent PNG (decode base64)
        fake_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        fake_png = base64.b64decode(fake_png_b64)
        mock_file_output.read.return_value = fake_png

        mock_client.run.return_value = [mock_file_output]

        return mock_client

    @pytest.mark.asyncio
    async def test_generate_cover_success(self, mock_replicate_client):
        """Test successful cover generation with flux-schnell."""
        # Arrange
        provider = ReplicateImageProvider(model="black-forest-labs/flux-schnell")
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Mock the client
        provider.client = mock_replicate_client

        # Act
        result = await provider.generate_cover(
            prompt="A colorful dinosaur cover", spec=spec, seed=42
        )

        # Assert
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify API was called with correct parameters
        mock_replicate_client.run.assert_called_once()
        call_args = mock_replicate_client.run.call_args

        # Check model
        assert call_args[0][0] == "black-forest-labs/flux-schnell"

        # Check input parameters
        input_params = call_args[1]["input"]
        assert "A colorful dinosaur cover" in input_params["prompt"]
        assert input_params["aspect_ratio"] == "1:1"
        assert input_params["num_outputs"] == 1
        assert input_params["output_format"] == "png"
        assert input_params["num_inference_steps"] == 4
        assert input_params["go_fast"] is True
        assert input_params["seed"] == 42

    @pytest.mark.asyncio
    async def test_generate_cover_with_bw_color_mode(self, mock_replicate_client):
        """Test cover generation with black & white color mode for coloring pages."""
        # Arrange
        provider = ReplicateImageProvider()
        provider.client = mock_replicate_client
        spec = ImageSpec(
            width_px=1024, height_px=1024, format="png", color_mode=ColorMode.BLACK_WHITE
        )

        # Act
        result = await provider.generate_cover(prompt="Dinosaur coloring page", spec=spec, seed=123)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

        # Verify prompt includes B&W instructions
        call_args = mock_replicate_client.run.call_args
        input_params = call_args[1]["input"]
        prompt_content = input_params["prompt"].lower()
        assert "black and white" in prompt_content
        assert "line art" in prompt_content

    @pytest.mark.asyncio
    async def test_generate_cover_tracks_usage(self, mock_replicate_client):
        """Test that cover generation tracks usage and cost."""
        # Arrange
        mock_tracker = AsyncMock()
        provider = ReplicateImageProvider(token_tracker=mock_tracker)
        provider.client = mock_replicate_client
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Act
        await provider.generate_cover(prompt="Test", spec=spec)

        # Assert
        mock_tracker.add_usage_metrics.assert_called_once()
        usage_metrics = mock_tracker.add_usage_metrics.call_args[0][0]

        # Verify cost tracking
        assert usage_metrics.model == "black-forest-labs/flux-schnell"
        assert usage_metrics.cost == Decimal("0.003")  # $0.003/image
        assert usage_metrics.prompt_tokens == 0  # Replicate doesn't expose tokens
        assert usage_metrics.completion_tokens == 0

    @pytest.mark.asyncio
    async def test_generate_cover_without_seed(self, mock_replicate_client):
        """Test cover generation without seed (randomized)."""
        # Arrange
        provider = ReplicateImageProvider()
        provider.client = mock_replicate_client
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Act
        result = await provider.generate_cover(prompt="Test", spec=spec, seed=None)

        # Assert
        assert result is not None

        # Verify seed is not included in params
        call_args = mock_replicate_client.run.call_args
        input_params = call_args[1]["input"]
        assert "seed" not in input_params

    @pytest.mark.asyncio
    async def test_generate_cover_handles_invalid_response(self):
        """Test that cover generation handles invalid API responses gracefully."""
        # Arrange
        provider = ReplicateImageProvider()
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Mock client with invalid response
        mock_client = MagicMock()
        mock_client.run.return_value = None  # Invalid response

        provider.client = mock_client

        # Act & Assert
        from backoffice.domain.errors.error_taxonomy import DomainError

        with pytest.raises(DomainError) as exc_info:
            await provider.generate_cover(prompt="Test", spec=spec)

        # Verify error details
        assert "Unexpected output format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_page_delegates_to_generate_cover(self, mock_replicate_client):
        """Test that generate_page delegates to generate_cover."""
        # Arrange
        provider = ReplicateImageProvider()
        provider.client = mock_replicate_client
        spec = ImageSpec(
            width_px=1024, height_px=1024, format="png", color_mode=ColorMode.BLACK_WHITE
        )

        # Act
        result = await provider.generate_page(prompt="Dinosaur page", spec=spec, seed=42)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

        # Verify same parameters as generate_cover
        mock_replicate_client.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_text_from_cover_success(self, mock_replicate_client):
        """Test successful text removal from cover."""
        import base64

        # Arrange
        provider = ReplicateImageProvider()
        provider.client = mock_replicate_client
        # Use valid PNG bytes
        fake_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        cover_bytes = base64.b64decode(fake_png_b64)

        # Act
        with patch("tempfile.NamedTemporaryFile"):
            with patch("os.unlink"):
                result = await provider.remove_text_from_cover(cover_bytes=cover_bytes)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

        # Verify text-removal model was called
        mock_replicate_client.run.assert_called_once()
        call_args = mock_replicate_client.run.call_args
        assert call_args[0][0] == "flux-kontext-apps/text-removal"

    @pytest.mark.asyncio
    async def test_remove_text_tracks_usage(self, mock_replicate_client):
        """Test that text removal tracks usage and cost."""
        import base64

        # Arrange
        mock_tracker = AsyncMock()
        provider = ReplicateImageProvider(token_tracker=mock_tracker)
        provider.client = mock_replicate_client

        # Use valid PNG bytes
        fake_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        cover_bytes = base64.b64decode(fake_png_b64)

        # Act
        with patch("tempfile.NamedTemporaryFile"):
            with patch("os.unlink"):
                await provider.remove_text_from_cover(cover_bytes=cover_bytes)

        # Assert
        mock_tracker.add_usage_metrics.assert_called_once()
        usage_metrics = mock_tracker.add_usage_metrics.call_args[0][0]

        # Verify cost tracking
        assert usage_metrics.model == "flux-kontext-apps/text-removal"
        assert usage_metrics.cost == Decimal("0.02")  # Estimated cost

    def test_provider_initializes_with_correct_model(self):
        """Test that provider stores the correct model."""
        # Arrange & Act
        provider = ReplicateImageProvider(model="custom/flux-model")

        # Assert
        assert provider.model == "custom/flux-model"

    def test_provider_uses_default_model(self):
        """Test that provider uses flux-schnell as default."""
        # Arrange & Act
        provider = ReplicateImageProvider()

        # Assert
        assert provider.model == "black-forest-labs/flux-schnell"

    def test_provider_uses_api_token_from_environment(self):
        """Test that provider loads API token from environment."""
        # Arrange & Act
        with patch.dict("os.environ", {"REPLICATE_API_TOKEN": "test-token"}):
            provider = ReplicateImageProvider()

        # Assert - client should be initialized (not None)
        assert provider.client is not None

    def test_provider_unavailable_without_token(self):
        """Test that provider is unavailable without API token."""
        # Arrange & Act
        with patch.dict("os.environ", {"REPLICATE_API_TOKEN": ""}, clear=True):
            provider = ReplicateImageProvider()

        # Assert
        assert provider.is_available() is False

    def test_provider_does_not_support_vectorization(self):
        """Test that Replicate provider doesn't support SVG vectorization."""
        # Arrange & Act
        provider = ReplicateImageProvider()

        # Assert
        assert provider.supports_vectorization() is False
