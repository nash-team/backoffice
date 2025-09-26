import pytest
from unittest.mock import patch

from backoffice.infrastructure.adapters.openai_image_generator import (
    OpenAIImageGenerator,
)

from tests.unit.infrastructure.adapters.fakes import FakeOpenAIService, FakeHTTPClient


@pytest.fixture
def fake_openai_service():
    """Fake OpenAI service"""
    return FakeOpenAIService()


@pytest.fixture
def image_generator():
    """Create OpenAI image generator with fake service"""
    fake_service = FakeOpenAIService()
    return OpenAIImageGenerator(fake_service)


@pytest.fixture
def unavailable_image_generator():
    """Create OpenAI image generator with unavailable service"""
    fake_service = FakeOpenAIService(available=False)
    return OpenAIImageGenerator(fake_service)


@pytest.mark.asyncio
async def test_generate_image_from_prompt_success(image_generator):
    """Test successful image generation from prompt"""
    # Arrange & Act
    result = await image_generator.generate_image_from_prompt(
        "A cute cat for coloring book", "1024x1024"
    )

    # Assert
    assert result == b"fake_image_data"


@pytest.mark.asyncio
async def test_generate_image_from_prompt_openai_unavailable(unavailable_image_generator):
    """Test fallback when OpenAI service is unavailable"""
    # Act
    result = await unavailable_image_generator.generate_image_from_prompt("test prompt")

    # Assert
    assert isinstance(result, bytes)
    assert len(result) > 0  # Should return fallback image


@pytest.mark.asyncio
async def test_generate_image_from_url_fallback_to_prompt(image_generator):
    """Test image generation from URL falls back to prompt-based generation"""
    # Arrange & Act
    fake_client = FakeHTTPClient()
    with patch("httpx.AsyncClient", return_value=fake_client):
        result = await image_generator.generate_image_from_url(
            "https://example.com/source.jpg", "test description"
        )

    # Assert
    assert result == b"fake_image_data"
    assert (
        len(fake_client.get_calls) == 1
    )  # Downloads original image only (no URL download for generated image with base64)


@pytest.mark.asyncio
async def test_generate_coloring_page_from_description(image_generator):
    """Test generating coloring page with specific styling"""
    # Arrange & Act
    result = await image_generator.generate_coloring_page_from_description("a beautiful flower")

    # Assert
    assert result == b"fake_image_data"


def test_is_available_with_client(image_generator):
    """Test availability check when client is available"""
    assert image_generator.is_available() is True


def test_is_available_without_client(unavailable_image_generator):
    """Test availability check when client is not available"""
    assert unavailable_image_generator.is_available() is False


@pytest.mark.asyncio
async def test_create_fallback_image():
    """Test creation of fallback image when OpenAI is unavailable"""
    # Arrange
    image_generator = OpenAIImageGenerator()

    # Act
    result = await image_generator._create_fallback_image()

    # Assert
    assert isinstance(result, bytes)
    assert len(result) > 0

    # Should be valid PNG data (starts with PNG signature)
    assert result.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.asyncio
async def test_generate_image_from_prompt_with_exception():
    """Test error handling when DALL-E call fails"""

    # Arrange - create failing service fake
    class FakeFailingOpenAIService:
        def __init__(self):
            self.client = FakeFailingOpenAIClient()

    class FakeFailingOpenAIClient:
        def __init__(self):
            self.images = FakeFailingImagesAPI()

    class FakeFailingImagesAPI:
        async def generate(self, *args, **kwargs):
            raise Exception("API Error")

    failing_generator = OpenAIImageGenerator(FakeFailingOpenAIService())

    # Act
    result = await failing_generator.generate_image_from_prompt("test prompt")

    # Assert
    # Should fall back to fallback image instead of raising exception
    assert isinstance(result, bytes)
    assert len(result) > 0
