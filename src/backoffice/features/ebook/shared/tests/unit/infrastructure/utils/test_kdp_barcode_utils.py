"""Unit tests for KDP barcode space reservation utilities."""

from io import BytesIO

import pytest
from PIL import Image

from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.barcode_utils import (
    add_barcode_space,
    generate_ean13_barcode,
)


@pytest.fixture
def sample_cover_image() -> bytes:
    """Create a sample 8.5" × 8.5" cover image @ 300 DPI (2550×2550px).

    Returns:
        PNG image bytes
    """
    # KDP square_format: 8.5" × 8.5" @ 300 DPI = 2550×2550px
    img = Image.new("RGB", (2550, 2550), color=(100, 150, 200))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_add_barcode_space_default_kdp_dimensions(sample_cover_image):
    """Test adding barcode space with default KDP dimensions (2.0" × 1.2" with 0.25" margin)."""
    result_bytes = add_barcode_space(sample_cover_image)

    # Verify result is valid image
    result_img = Image.open(BytesIO(result_bytes))
    assert result_img.size == (2550, 2550)  # Same size as input

    # Verify white rectangle exists at bottom-right
    # KDP specs @ 300 DPI:
    # - Barcode: 2.0" × 1.2" = 600×360px
    # - Margin: 0.25" = 75px

    # Expected white rectangle position:
    # x1 = 2550 - 600 - 75 = 1875
    # y1 = 2550 - 360 - 75 = 2115
    # x2 = 2550 - 75 = 2475
    # y2 = 2550 - 75 = 2475

    # Sample pixels inside barcode area (should be white)
    center_barcode = result_img.getpixel((2100, 2300))  # Inside barcode area
    assert center_barcode == (255, 255, 255), "Barcode area should be white"

    # Sample pixels outside barcode area (should NOT be white)
    top_left = result_img.getpixel((100, 100))
    assert top_left != (255, 255, 255), "Non-barcode area should not be white"


def test_add_barcode_space_custom_dimensions(sample_cover_image):
    """Test adding barcode space with custom dimensions."""
    # Custom smaller barcode: 1.0" × 0.75" with 0.125" margin
    result_bytes = add_barcode_space(
        sample_cover_image,
        barcode_width_inches=1.0,
        barcode_height_inches=0.75,
        barcode_margin_inches=0.125,
    )

    result_img = Image.open(BytesIO(result_bytes))

    # Verify white rectangle exists
    # Custom @ 300 DPI:
    # - Barcode: 1.0" × 0.75" = 300×225px
    # - Margin: 0.125" = 38px (rounded to even: 38px)

    # Sample pixel inside custom barcode area
    # x1 = 2550 - 300 - 38 = 2212
    # y1 = 2550 - 226 - 38 = 2286 (225px rounded to even = 226px)
    center_barcode = result_img.getpixel((2350, 2400))
    assert center_barcode == (255, 255, 255), "Custom barcode area should be white"


def test_add_barcode_space_preserves_format(sample_cover_image):
    """Test that the output format is preserved (PNG)."""
    result_bytes = add_barcode_space(sample_cover_image)

    # Verify it's a valid PNG
    result_img = Image.open(BytesIO(result_bytes))
    assert result_img.format == "PNG"


def test_add_barcode_space_on_small_image():
    """Test adding barcode space on a small image (should fallback gracefully)."""
    # Create tiny image (smaller than barcode dimensions)
    small_img = Image.new("RGB", (200, 200), color=(50, 100, 150))
    buffer = BytesIO()
    small_img.save(buffer, format="PNG")
    small_bytes = buffer.getvalue()

    # Should not crash, should fallback to percentage-based
    result_bytes = add_barcode_space(small_bytes)

    result_img = Image.open(BytesIO(result_bytes))
    assert result_img.size == (200, 200)

    # Should still have a white rectangle (smaller, percentage-based)
    # Check bottom-right area
    bottom_right = result_img.getpixel((180, 180))
    assert bottom_right == (255, 255, 255), "Small image should have white barcode area"


def test_add_barcode_space_invalid_image():
    """Test handling of invalid image data."""
    invalid_bytes = b"not an image"

    with pytest.raises(ValueError, match="Failed to add barcode space"):
        add_barcode_space(invalid_bytes)


def test_add_barcode_space_exact_kdp_compliance():
    """Test exact KDP barcode dimensions compliance.

    KDP specs:
    - Width: 2.0" = 600px @ 300 DPI
    - Height: 1.2" = 360px @ 300 DPI
    - Margin: 0.25" = 75px @ 300 DPI
    """
    # Create exact KDP size cover (8.5" × 8.5" @ 300 DPI)
    kdp_cover = Image.new("RGB", (2550, 2550), color=(80, 120, 160))
    buffer = BytesIO()
    kdp_cover.save(buffer, format="PNG")
    kdp_bytes = buffer.getvalue()

    result_bytes = add_barcode_space(kdp_bytes)
    result_img = Image.open(BytesIO(result_bytes))

    # Verify exact white rectangle bounds
    # x1 = 2550 - 600 - 75 = 1875
    # y1 = 2550 - 360 - 75 = 2115
    # x2 = 2550 - 75 = 2475
    # y2 = 2550 - 75 = 2475

    # Test corners of white rectangle
    top_left_barcode = result_img.getpixel((1876, 2116))  # Just inside top-left
    assert top_left_barcode == (255, 255, 255)

    top_right_barcode = result_img.getpixel((2474, 2116))  # Just inside top-right
    assert top_right_barcode == (255, 255, 255)

    bottom_left_barcode = result_img.getpixel((1876, 2474))  # Just inside bottom-left
    assert bottom_left_barcode == (255, 255, 255)

    bottom_right_barcode = result_img.getpixel((2474, 2474))  # Just inside bottom-right
    assert bottom_right_barcode == (255, 255, 255)

    # Test pixels just outside rectangle (should NOT be white)
    above_rectangle = result_img.getpixel((2100, 2110))  # Above barcode
    assert above_rectangle != (255, 255, 255), "Area above barcode should not be white"

    left_of_rectangle = result_img.getpixel((1870, 2300))  # Left of barcode
    assert left_of_rectangle != (255, 255, 255), "Area left of barcode should not be white"


# ---------------------------------------------------------------------------
# EAN-13 barcode generation tests
# ---------------------------------------------------------------------------


class TestGenerateEAN13Barcode:
    """Tests for generate_ean13_barcode function."""

    def test_valid_isbn_generates_barcode(self) -> None:
        barcode_img = generate_ean13_barcode("9781234567897")
        assert barcode_img.size == (600, 360)
        assert barcode_img.mode == "RGB"

    def test_custom_dimensions(self) -> None:
        barcode_img = generate_ean13_barcode("9781234567897", target_width_px=300, target_height_px=180)
        assert barcode_img.size == (300, 180)

    def test_barcode_has_black_bars(self) -> None:
        """Barcode should contain both dark bars and white spaces."""
        barcode_img = generate_ean13_barcode("9781234567897")
        # Scan horizontal line across barcode for both dark and white pixels
        has_dark = False
        has_white = False
        for x in range(50, 550, 5):
            px = barcode_img.getpixel((x, 150))
            if px[0] < 50 and px[1] < 50 and px[2] < 50:
                has_dark = True
            if px[0] > 200 and px[1] > 200 and px[2] > 200:
                has_white = True
            if has_dark and has_white:
                break
        assert has_dark and has_white, "Barcode should have both dark bars and white spaces"

    def test_invalid_isbn_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Failed to generate barcode"):
            generate_ean13_barcode("invalid")


class TestAddBarcodeSpaceWithISBN:
    """Tests for add_barcode_space with ISBN parameter."""

    def test_with_isbn_renders_barcode(self, sample_cover_image: bytes) -> None:
        """With ISBN, barcode zone should contain non-white pixels."""
        result_bytes = add_barcode_space(sample_cover_image, isbn="9781234567897")
        result_img = Image.open(BytesIO(result_bytes))

        # Scan barcode area for non-white pixels
        found_non_white = False
        for x in range(1900, 2400, 20):
            for y in range(2150, 2450, 20):
                pixel = result_img.getpixel((x, y))
                if pixel != (255, 255, 255):
                    found_non_white = True
                    break
            if found_non_white:
                break
        assert found_non_white, "Barcode area should contain barcode bars (non-white pixels)"

    def test_without_isbn_stays_white(self, sample_cover_image: bytes) -> None:
        """Without ISBN, barcode zone should be plain white (backward compat)."""
        result_bytes = add_barcode_space(sample_cover_image)
        result_img = Image.open(BytesIO(result_bytes))
        center_barcode = result_img.getpixel((2100, 2300))
        assert center_barcode == (255, 255, 255), "Without ISBN, barcode area should be white"
