import pytest

from backoffice.domain.entities.image_page import (
    ColoringPageRequest,
    ImageFormat,
    ImagePage,
    ImagePageType,
)


def test_image_page_creation():
    """Test creating an image page with all attributes"""
    # Arrange & Act
    page = ImagePage(
        title="Test Coloring Page",
        image_data=b"fake_svg_data",
        image_format=ImageFormat.SVG,
        page_type=ImagePageType.COLORING_PAGE,
        description="A beautiful test page",
        full_bleed=True,
        maintain_aspect_ratio=False,
        background_color="white",
    )

    # Assert
    assert page.title == "Test Coloring Page"
    assert page.image_data == b"fake_svg_data"
    assert page.image_format == ImageFormat.SVG
    assert page.page_type == ImagePageType.COLORING_PAGE
    assert page.description == "A beautiful test page"
    assert page.full_bleed is True
    assert page.maintain_aspect_ratio is False
    assert page.background_color == "white"
    assert page.width_mm == 210  # A4 default
    assert page.height_mm == 297  # A4 default
    assert page.margin_mm == 0  # No margin for full-bleed


def test_image_page_defaults():
    """Test default values for optional attributes"""
    # Arrange & Act
    page = ImagePage(
        title="Test Page",
        image_data=b"test_data",
        image_format=ImageFormat.PNG,
        page_type=ImagePageType.ILLUSTRATION,
    )

    # Assert
    assert page.description is None
    assert page.full_bleed is True
    assert page.maintain_aspect_ratio is True
    assert page.background_color == "white"


def test_get_svg_content_success():
    """Test getting SVG content as string"""
    # Arrange
    svg_data = b"<svg>test content</svg>"
    page = ImagePage(
        title="SVG Page",
        image_data=svg_data,
        image_format=ImageFormat.SVG,
        page_type=ImagePageType.COLORING_PAGE,
    )

    # Act
    result = page.get_svg_content()

    # Assert
    assert result == "<svg>test content</svg>"


def test_get_svg_content_non_svg_raises_error():
    """Test getting SVG content from non-SVG page raises ValueError"""
    # Arrange
    page = ImagePage(
        title="PNG Page",
        image_data=b"png_data",
        image_format=ImageFormat.PNG,
        page_type=ImagePageType.COLORING_PAGE,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Image is not in SVG format"):
        page.get_svg_content()


def test_is_vector_svg():
    """Test is_vector returns True for SVG"""
    # Arrange
    page = ImagePage(
        title="SVG Page",
        image_data=b"svg_data",
        image_format=ImageFormat.SVG,
        page_type=ImagePageType.COLORING_PAGE,
    )

    # Act & Assert
    assert page.is_vector() is True


def test_is_vector_non_svg():
    """Test is_vector returns False for non-SVG formats"""
    # Arrange
    png_page = ImagePage(
        title="PNG Page",
        image_data=b"png_data",
        image_format=ImageFormat.PNG,
        page_type=ImagePageType.COLORING_PAGE,
    )

    jpeg_page = ImagePage(
        title="JPEG Page",
        image_data=b"jpeg_data",
        image_format=ImageFormat.JPEG,
        page_type=ImagePageType.ILLUSTRATION,
    )

    # Act & Assert
    assert png_page.is_vector() is False
    assert jpeg_page.is_vector() is False


def test_get_css_size_full_bleed():
    """Test CSS size generation for full-bleed images"""
    # Arrange
    page = ImagePage(
        title="Full Bleed Page",
        image_data=b"data",
        image_format=ImageFormat.SVG,
        page_type=ImagePageType.COLORING_PAGE,
        full_bleed=True,
    )

    # Act
    result = page.get_css_size()

    # Assert
    assert result == "width: 100%; height: 100%; object-fit: cover;"


def test_get_css_size_not_full_bleed_maintain_aspect():
    """Test CSS size for non-full-bleed with aspect ratio maintained"""
    # Arrange
    page = ImagePage(
        title="Normal Page",
        image_data=b"data",
        image_format=ImageFormat.PNG,
        page_type=ImagePageType.ILLUSTRATION,
        full_bleed=False,
        maintain_aspect_ratio=True,
    )

    # Act
    result = page.get_css_size()

    # Assert
    assert result == "width: 100%; height: 100%; object-fit: contain;"


def test_get_css_size_not_full_bleed_no_aspect():
    """Test CSS size for non-full-bleed without aspect ratio maintained"""
    # Arrange
    page = ImagePage(
        title="Stretched Page",
        image_data=b"data",
        image_format=ImageFormat.PNG,
        page_type=ImagePageType.ILLUSTRATION,
        full_bleed=False,
        maintain_aspect_ratio=False,
    )

    # Act
    result = page.get_css_size()

    # Assert
    assert result == "width: 100%; height: 100%; object-fit: fill;"


def test_coloring_page_request_with_url():
    """Test creating coloring page request with URL"""
    # Act
    request = ColoringPageRequest(
        source_url="https://example.com/image.jpg",
        title="Test Coloring Page",
    )

    # Assert
    assert request.source_url == "https://example.com/image.jpg"
    assert request.description is None
    assert request.title == "Test Coloring Page"
    assert request.generate_from_ai is False


def test_coloring_page_request_with_description():
    """Test creating coloring page request with AI description"""
    # Act
    request = ColoringPageRequest(
        description="A cute cat playing",
        title="Cat Page",
        generate_from_ai=True,
    )

    # Assert
    assert request.source_url is None
    assert request.description == "A cute cat playing"
    assert request.title == "Cat Page"
    assert request.generate_from_ai is True


def test_coloring_page_request_defaults():
    """Test default values for coloring page request"""
    # Act
    request = ColoringPageRequest(source_url="https://example.com/image.jpg")

    # Assert
    assert request.title == "Page de coloriage"
    assert request.generate_from_ai is False


def test_coloring_page_request_validation_no_source():
    """Test validation fails when no source is provided"""
    # Act & Assert
    with pytest.raises(ValueError, match="Either source_url or description must be provided"):
        ColoringPageRequest()


def test_coloring_page_request_validation_description_without_ai():
    """Test validation fails when description provided without generate_from_ai=True"""
    # Act & Assert
    with pytest.raises(ValueError, match="description requires generate_from_ai to be True"):
        ColoringPageRequest(
            description="A cat",
            generate_from_ai=False,
        )


def test_image_page_type_enum_values():
    """Test ImagePageType enum values"""
    assert ImagePageType.COLORING_PAGE.value == "coloring_page"
    assert ImagePageType.ILLUSTRATION.value == "illustration"
    assert ImagePageType.COVER_IMAGE.value == "cover_image"
    assert ImagePageType.SEPARATOR.value == "separator"


def test_image_format_enum_values():
    """Test ImageFormat enum values"""
    assert ImageFormat.SVG.value == "svg"
    assert ImageFormat.PNG.value == "png"
    assert ImageFormat.JPEG.value == "jpeg"
