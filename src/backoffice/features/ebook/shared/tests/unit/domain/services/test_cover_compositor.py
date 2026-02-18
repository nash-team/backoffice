"""Unit tests for CoverCompositor."""

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from backoffice.features.ebook.shared.domain.services.cover_compositor import (
    FOOTER_BOTTOM_PADDING_PX,
    PADDING_PX,
    CoverCompositor,
)


def _make_png(width: int, height: int, color: str = "blue") -> bytes:
    """Create a valid PNG image."""
    img = Image.new("RGBA", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _save_png(path: Path, width: int, height: int, color: str = "red") -> None:
    """Save a PNG image to disk."""
    img = Image.new("RGBA", (width, height), color)
    img.save(path, format="PNG")


@pytest.fixture()
def _allow_tmp_paths(tmp_path: Path):
    """Allow tmp_path as a valid overlay prefix for tests."""
    with patch(
        "backoffice.features.ebook.shared.domain.services.cover_compositor._ALLOWED_OVERLAY_PREFIXES",
        (str(tmp_path) + "/",),
    ):
        yield


class TestCoverCompositor:
    """Tests for CoverCompositor."""

    @pytest.mark.usefixtures("_allow_tmp_paths")
    def test_compose_cover_with_title_and_footer(self, tmp_path: Path) -> None:
        """Test compositing both title and footer onto base cover."""
        compositor = CoverCompositor()

        base_cover = _make_png(2626, 2626, "green")
        title_path = tmp_path / "title.png"
        footer_path = tmp_path / "footer.png"
        _save_png(title_path, 800, 200, "red")
        _save_png(footer_path, 600, 100, "yellow")

        result = compositor.compose_cover(
            base_cover=base_cover,
            title_image_path=str(title_path),
            footer_image_path=str(footer_path),
        )

        # Result should be valid PNG
        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (2626, 2626)

    @pytest.mark.usefixtures("_allow_tmp_paths")
    def test_compose_cover_title_centered_horizontally(self, tmp_path: Path) -> None:
        """Test that title is centered horizontally."""
        compositor = CoverCompositor()

        base_cover = _make_png(2626, 2626, "white")
        title_path = tmp_path / "title.png"
        # Red title on transparent background
        title_img = Image.new("RGBA", (400, 100), (255, 0, 0, 255))
        title_img.save(title_path, format="PNG")

        result = compositor.compose_cover(
            base_cover=base_cover,
            title_image_path=str(title_path),
            footer_image_path="",
        )

        result_img = Image.open(io.BytesIO(result))
        # Title should be at x = (2626 - 400) / 2 = 1113, y = PADDING_PX
        # Check pixel at center of title area is red
        center_x = 2626 // 2
        pixel = result_img.getpixel((center_x, PADDING_PX + 50))
        assert pixel[0] == 255  # Red channel
        assert pixel[1] == 0  # Green channel

    @pytest.mark.usefixtures("_allow_tmp_paths")
    def test_compose_cover_footer_at_bottom(self, tmp_path: Path) -> None:
        """Test that footer is positioned at the bottom."""
        compositor = CoverCompositor()

        base_cover = _make_png(2626, 2626, "white")
        footer_path = tmp_path / "footer.png"
        footer_height = 100
        footer_img = Image.new("RGBA", (400, footer_height), (0, 0, 255, 255))
        footer_img.save(footer_path, format="PNG")

        result = compositor.compose_cover(
            base_cover=base_cover,
            title_image_path="",
            footer_image_path=str(footer_path),
        )

        result_img = Image.open(io.BytesIO(result))
        # Footer bottom edge should be at cover_height - FOOTER_BOTTOM_PADDING_PX
        footer_y = 2626 - FOOTER_BOTTOM_PADDING_PX - footer_height
        center_x = 2626 // 2
        pixel = result_img.getpixel((center_x, footer_y + 50))
        assert pixel[2] == 255  # Blue channel

    def test_compose_cover_invalid_paths_skipped(self) -> None:
        """Test that invalid overlay paths are gracefully skipped."""
        compositor = CoverCompositor()

        base_cover = _make_png(500, 500, "green")

        result = compositor.compose_cover(
            base_cover=base_cover,
            title_image_path="/etc/passwd",
            footer_image_path="../../../secret.png",
        )

        # Should return a valid image (just the base, re-encoded)
        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (500, 500)

    def test_compose_cover_empty_paths_skipped(self) -> None:
        """Test that empty overlay paths are gracefully skipped."""
        compositor = CoverCompositor()

        base_cover = _make_png(500, 500, "green")

        result = compositor.compose_cover(
            base_cover=base_cover,
            title_image_path="",
            footer_image_path="",
        )

        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (500, 500)

    @pytest.mark.usefixtures("_allow_tmp_paths")
    def test_compose_cover_missing_files_skipped(self, tmp_path: Path) -> None:
        """Test that missing overlay files are gracefully skipped."""
        compositor = CoverCompositor()

        base_cover = _make_png(500, 500, "green")

        result = compositor.compose_cover(
            base_cover=base_cover,
            title_image_path=str(tmp_path / "nonexistent_title.png"),
            footer_image_path=str(tmp_path / "nonexistent_footer.png"),
        )

        # Should return a valid image (just the base, re-encoded)
        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (500, 500)

    @pytest.mark.usefixtures("_allow_tmp_paths")
    def test_compose_cover_oversized_title_resized(self, tmp_path: Path) -> None:
        """Test that title wider than cover is resized proportionally."""
        compositor = CoverCompositor()

        cover_size = 1000
        base_cover = _make_png(cover_size, cover_size, "white")
        title_path = tmp_path / "title.png"
        # Title wider than max overlay width (cover_size - 2 * PADDING_PX)
        _save_png(title_path, 5000, 500, "red")

        result = compositor.compose_cover(
            base_cover=base_cover,
            title_image_path=str(title_path),
            footer_image_path="",
        )

        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (cover_size, cover_size)

    @pytest.mark.usefixtures("_allow_tmp_paths")
    def test_compose_cover_tall_overlay_constrained_by_height(self, tmp_path: Path) -> None:
        """Test that overlays taller than max ratio are shrunk by height, not just width."""
        compositor = CoverCompositor()

        cover_size = 1024
        base_cover = _make_png(cover_size, cover_size, "white")
        title_path = tmp_path / "title.png"
        # 1536x1024 overlay (same aspect as real assets) — much taller than 25% of 1024
        _save_png(title_path, 1536, 1024, "red")

        result = compositor.compose_cover(
            base_cover=base_cover,
            title_image_path=str(title_path),
            footer_image_path="",
        )

        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (cover_size, cover_size)

        # Title should NOT extend past 25% of cover height + padding
        # max_title_height = 1024 * 0.25 = 256
        # With 1536x1024 overlay, height-constrained: ratio = 256/1024 = 0.25
        # Result: 384x256 — well within bounds
        # Check that the area below title zone is still white (not red)
        mid_y = cover_size // 2
        center_x = cover_size // 2
        pixel = result_img.getpixel((center_x, mid_y))
        assert pixel[0] == 255  # White — title didn't reach here
        assert pixel[1] == 255


class TestCoverCompositorPathValidation:
    """Tests for path validation security."""

    def test_rejects_absolute_paths(self) -> None:
        """Test that absolute paths outside allowed dirs are rejected."""
        assert not CoverCompositor._validate_overlay_path("/etc/passwd")
        assert not CoverCompositor._validate_overlay_path("/tmp/evil.png")

    def test_rejects_path_traversal(self) -> None:
        """Test that path traversal attempts are rejected."""
        assert not CoverCompositor._validate_overlay_path("../../../etc/passwd")
        assert not CoverCompositor._validate_overlay_path("config/branding/../../etc/passwd")

    def test_accepts_allowed_prefix(self) -> None:
        """Test that paths under config/branding/ are accepted."""
        assert CoverCompositor._validate_overlay_path("config/branding/themes/assets/dinosaurs/cover_title.png")
        assert CoverCompositor._validate_overlay_path("config/branding/assets/cover_footer.png")

    def test_rejects_empty_path(self) -> None:
        """Test that empty path is rejected."""
        assert not CoverCompositor._validate_overlay_path("")

    def test_rejects_unrelated_prefix(self) -> None:
        """Test that paths outside allowed prefixes are rejected."""
        assert not CoverCompositor._validate_overlay_path("src/backoffice/evil.png")
        assert not CoverCompositor._validate_overlay_path("storage/uploads/evil.png")
