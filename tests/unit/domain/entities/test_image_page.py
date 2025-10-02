from backoffice.domain.entities.image_page import (
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
