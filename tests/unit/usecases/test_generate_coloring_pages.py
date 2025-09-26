import pytest

from backoffice.domain.entities.image_page import (
    ColoringPageRequest,
    ImageFormat,
    ImagePage,
    ImagePageType,
)
from backoffice.domain.usecases.generate_coloring_pages import GenerateColoringPagesUseCase
from tests.unit.infrastructure.adapters.fakes import (
    FakeImageGenerator,
    FakeVectorizer,
    FakeFailingImageGenerator,
    FakeFailingVectorizer,
)


@pytest.fixture
def fake_image_generator():
    return FakeImageGenerator()


@pytest.fixture
def fake_vectorizer():
    return FakeVectorizer()


@pytest.fixture
def use_case(fake_image_generator, fake_vectorizer):
    return GenerateColoringPagesUseCase(fake_image_generator, fake_vectorizer)


@pytest.mark.asyncio
async def test_generate_coloring_pages_from_urls(use_case, fake_image_generator, fake_vectorizer):
    """Test generating coloring pages from image URLs with SVG conversion"""
    # Arrange
    requests = [
        ColoringPageRequest(
            source_url="https://example.com/image1.jpg",
            title="Page 1",
        ),
        ColoringPageRequest(
            source_url="https://example.com/image2.png",
            title="Page 2",
        ),
    ]

    # Act
    result = await use_case.execute(requests, convert_to_svg=True)

    # Assert
    assert len(result) == 2

    # Check first page
    page1 = result[0]
    assert isinstance(page1, ImagePage)
    assert page1.title == "Page 1"
    assert page1.image_format == ImageFormat.SVG
    assert page1.page_type == ImagePageType.COLORING_PAGE
    assert page1.full_bleed is True
    assert page1.image_data == b"<svg>fake_optimized_svg</svg>"

    # Check second page
    page2 = result[1]
    assert page2.title == "Page 2"
    assert page2.image_format == ImageFormat.SVG

    # Verify service calls
    assert len(fake_image_generator.generate_image_from_url_calls) == 2
    assert len(fake_vectorizer.vectorize_image_calls) == 2
    assert len(fake_vectorizer.optimize_for_coloring_calls) == 2


@pytest.mark.asyncio
async def test_generate_coloring_pages_from_description(use_case, fake_image_generator):
    """Test generating coloring pages from AI descriptions"""
    # Arrange
    requests = [
        ColoringPageRequest(
            description="A cute cat playing with yarn",
            title="Cat Coloring Page",
            generate_from_ai=True,
        ),
    ]

    # Act
    result = await use_case.execute(requests, convert_to_svg=False)

    # Assert
    assert len(result) == 1
    page = result[0]
    assert page.title == "Cat Coloring Page"
    assert page.image_format == ImageFormat.PNG  # No SVG conversion
    assert page.image_data == b"fake_coloring_page"

    # Verify correct method was called
    assert len(fake_image_generator.generate_coloring_page_from_description_calls) == 1
    assert (
        fake_image_generator.generate_coloring_page_from_description_calls[0]
        == "A cute cat playing with yarn"
    )


@pytest.mark.asyncio
async def test_generate_coloring_pages_vectorization_failure_fallback():
    """Test fallback to PNG when SVG vectorization fails"""
    # Arrange
    fake_image_generator = FakeImageGenerator()
    fake_vectorizer = FakeFailingVectorizer()
    use_case = GenerateColoringPagesUseCase(fake_image_generator, fake_vectorizer)

    requests = [
        ColoringPageRequest(
            source_url="https://example.com/image.jpg",
            title="Test Page",
        ),
    ]

    # Act
    result = await use_case.execute(requests, convert_to_svg=True)

    # Assert
    assert len(result) == 1
    page = result[0]
    assert page.image_format == ImageFormat.PNG  # Fell back to PNG
    assert page.image_data == b"fake_image_from_url"


@pytest.mark.asyncio
async def test_generate_coloring_pages_with_complete_failure():
    """Test fallback SVG generation when both image generation and vectorization fail"""
    # Arrange
    fake_image_generator = FakeFailingImageGenerator()
    fake_vectorizer = FakeFailingVectorizer()
    use_case = GenerateColoringPagesUseCase(fake_image_generator, fake_vectorizer)

    requests = [
        ColoringPageRequest(
            source_url="https://example.com/image.jpg",
            title="Failed Page",
        ),
    ]

    # Act
    result = await use_case.execute(requests)

    # Assert
    assert len(result) == 1
    page = result[0]
    assert page.title == "Failed Page"
    assert page.image_format == ImageFormat.SVG  # Fallback SVG
    assert b"Erreur de g" in page.image_data  # Contains error text in French
    assert page.description and "Fake image generation failure" in page.description


def test_parse_image_urls_valid_urls(use_case):
    """Test parsing valid image URLs from text input"""
    # Arrange
    url_text = """https://example.com/image1.jpg
https://example.com/image2.png
https://test.org/photo.jpeg"""

    # Act
    requests = use_case.parse_image_urls(url_text)

    # Assert
    assert len(requests) == 3
    assert requests[0].source_url == "https://example.com/image1.jpg"
    assert requests[0].title == "Page de coloriage 1"
    assert requests[1].source_url == "https://example.com/image2.png"
    assert requests[1].title == "Page de coloriage 2"
    assert requests[2].source_url == "https://test.org/photo.jpeg"
    assert requests[2].title == "Page de coloriage 3"


def test_parse_image_urls_with_invalid_urls(use_case):
    """Test parsing URLs with some invalid entries"""
    # Arrange
    url_text = """https://example.com/image1.jpg
not-a-url
ftp://invalid-protocol.com/image.png
https://valid.com/image2.jpg

"""

    # Act
    requests = use_case.parse_image_urls(url_text)

    # Assert
    assert len(requests) == 2  # Only valid HTTPS/HTTP URLs
    assert requests[0].source_url == "https://example.com/image1.jpg"
    assert requests[1].source_url == "https://valid.com/image2.jpg"


def test_parse_image_urls_empty_input(use_case):
    """Test parsing empty or whitespace input"""
    # Act
    requests_empty = use_case.parse_image_urls("")
    requests_whitespace = use_case.parse_image_urls("   \n\n   ")

    # Assert
    assert len(requests_empty) == 0
    assert len(requests_whitespace) == 0


@pytest.mark.asyncio
async def test_generate_coloring_pages_invalid_request(use_case):
    """Test handling invalid coloring page request"""
    # Arrange - request with neither URL nor description
    with pytest.raises(ValueError, match="Either source_url or description"):
        ColoringPageRequest()  # Should raise during initialization
