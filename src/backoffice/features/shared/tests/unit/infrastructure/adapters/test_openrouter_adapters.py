"""Unit tests for OpenRouter adapters (cover and image generation)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backoffice.features.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.shared.infrastructure.providers.openrouter_image_provider import (
    OpenRouterImageProvider,
)


class TestOpenRouterImageProvider:
    """Tests for OpenRouter image generation adapter."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing."""
        mock_client = MagicMock()
        mock_response = MagicMock()

        # Mock the chat.completions.create response
        # Gemini 2.5 returns images in message.images array
        mock_message = MagicMock()
        mock_message.content = ""  # Text content is usually empty when image is returned
        mock_message.images = [
            {
                "image_url": {
                    "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                }
            }
        ]

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        return mock_client

    @pytest.mark.asyncio
    async def test_generate_cover_success(self, mock_openai_client):
        """Test successful cover generation."""
        # Arrange
        provider = OpenRouterImageProvider(model="google/gemini-2.5-flash-image-preview")
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Mock the client
        provider.client = mock_openai_client

        # Act
        result = await provider.generate_cover(
            prompt="A colorful dinosaur cover", spec=spec, seed=42
        )

        # Assert
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify API was called with correct parameters
        mock_openai_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs

        assert call_kwargs["model"] == "google/gemini-2.5-flash-image-preview"
        assert "extra_body" in call_kwargs
        assert call_kwargs["extra_body"]["modalities"] == ["image", "text"]

        # Verify prompt includes cover instructions
        messages = call_kwargs["messages"]
        prompt_content = messages[0]["content"].lower()
        assert "colorful" in prompt_content and "cover" in prompt_content

    @pytest.mark.asyncio
    async def test_generate_cover_uses_default_model(self, mock_openai_client):
        """Test that provider uses default model when none specified."""
        # Arrange
        with patch.dict("os.environ", {"LLM_IMAGE_MODEL": "google/gemini-custom-image"}):
            provider = OpenRouterImageProvider()

        provider.client = mock_openai_client
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Act
        result = await provider.generate_cover(prompt="Test cover", spec=spec)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

        # Should use environment variable model
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "google/gemini-custom-image"

    @pytest.mark.asyncio
    async def test_generate_cover_with_bw_color_mode(self, mock_openai_client):
        """Test cover generation with black & white color mode for coloring pages."""
        # Arrange
        provider = OpenRouterImageProvider()
        provider.client = mock_openai_client
        spec = ImageSpec(
            width_px=1024, height_px=1024, format="png", color_mode=ColorMode.BLACK_WHITE
        )

        # Act - Use prompt that includes B&W instructions
        prompt = "Black and white line art dinosaur coloring page"
        result = await provider.generate_cover(prompt=prompt, spec=spec, seed=123)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

        # Verify prompt was passed correctly
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        prompt_content = messages[0]["content"].lower()
        assert "coloring page" in prompt_content

    @pytest.mark.asyncio
    async def test_generate_cover_handles_invalid_response(self):
        """Test that cover generation handles invalid API responses gracefully."""
        # Arrange
        provider = OpenRouterImageProvider()
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Mock client with invalid response (no images, no content)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = ""  # Empty content
        mock_message.images = None  # No images
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider.client = mock_client

        # Act & Assert
        from backoffice.features.shared.domain.errors.error_taxonomy import DomainError

        with pytest.raises(DomainError) as exc_info:
            await provider.generate_cover(prompt="Test", spec=spec)

        # Verify error details
        assert "Failed to extract image" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_cover_includes_modalities(self, mock_openai_client):
        """Test that cover generation includes required modalities for Gemini."""
        # Arrange
        provider = OpenRouterImageProvider(model="google/gemini-2.5-flash-image-preview")
        provider.client = mock_openai_client
        spec = ImageSpec(width_px=1024, height_px=1024, format="png", color_mode=ColorMode.COLOR)

        # Act
        await provider.generate_cover(prompt="Test", spec=spec)

        # Assert - Verify modalities are included
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert "extra_body" in call_kwargs
        assert call_kwargs["extra_body"]["modalities"] == ["image", "text"]

    def test_provider_initializes_with_correct_model(self):
        """Test that provider stores the correct model."""
        # Arrange & Act
        provider = OpenRouterImageProvider(model="custom/model")

        # Assert
        assert provider.model == "custom/model"

    def test_provider_uses_api_key_from_environment(self):
        """Test that provider loads API key from environment."""
        # Arrange & Act
        with patch.dict("os.environ", {"LLM_API_KEY": "test-api-key"}):
            provider = OpenRouterImageProvider()

        # Assert - client should be initialized (not None)
        assert provider.client is not None
