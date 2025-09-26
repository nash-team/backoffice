import pytest
from unittest.mock import patch, MagicMock

from backoffice.infrastructure.adapters.potrace_vectorizer import PotraceVectorizer


@pytest.fixture
def vectorizer():
    return PotraceVectorizer()


def test_is_available_with_potrace_installed(vectorizer):
    """Test availability check when Potrace is installed"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        assert vectorizer.is_available() is True


def test_is_available_potrace_not_installed(vectorizer):
    """Test availability check when Potrace is not installed"""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert vectorizer.is_available() is False


@pytest.mark.asyncio
async def test_vectorize_image_potrace_not_available(vectorizer):
    """Test fallback when Potrace is not available"""
    mock_image_data = b"fake_png_data"

    with patch.object(vectorizer, "is_available", return_value=False):
        result = await vectorizer.vectorize_image(mock_image_data)

        # Should return fallback SVG
        assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<svg" in result
        assert "Coloring Page" in result


@pytest.mark.asyncio
async def test_optimize_for_coloring_valid_svg(vectorizer):
    """Test SVG optimization for coloring book style"""
    input_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path d="M10,10 L90,90" fill="red"/>
  <circle cx="50" cy="50" r="20" fill="blue"/>
</svg>"""

    result = await vectorizer.optimize_for_coloring(input_svg)

    assert 'stroke="black"' in result
    assert 'stroke-width="3"' in result
    assert 'fill="none"' in result
    assert 'viewBox="0 0 1024 1024"' in result
    assert 'fill="white"' in result  # Should add white background


@pytest.mark.asyncio
async def test_optimize_for_coloring_invalid_svg(vectorizer):
    """Test SVG optimization with invalid input returns original"""
    invalid_svg = "not valid xml"
    result = await vectorizer.optimize_for_coloring(invalid_svg)
    assert result == invalid_svg


@pytest.mark.asyncio
async def test_create_fallback_svg(vectorizer):
    """Test creation of fallback SVG"""
    result = await vectorizer._create_fallback_svg()

    assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<svg" in result
    assert "Coloring Page" in result
    assert 'stroke="black"' in result


@pytest.mark.asyncio
async def test_convert_png_to_svg_fallback(vectorizer):
    """Test PNG to SVG embedding fallback"""
    mock_image_data = b"fake_png_data"

    with patch("PIL.Image.open") as mock_image_open, patch("base64.b64encode") as mock_b64encode:
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        mock_image_open.return_value = mock_image

        mock_b64encode.return_value = b"encoded_image_data"

        result = await vectorizer.convert_png_to_svg_fallback(mock_image_data)

        assert "data:image/png;base64,encoded_image_data" in result
        assert 'width="800"' in result
        assert 'height="600"' in result
        assert "<?xml version" in result
