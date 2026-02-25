"""Unit tests for CoverCompositor."""

import io
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from backoffice.features.ebook.shared.domain.entities.theme_profile import BackCoverConfig
from backoffice.features.ebook.shared.domain.services.cover_compositor import (
    BACK_COVER_CREDITS_BOTTOM_PX,
    BACK_COVER_PREVIEW_TOP_PX,
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
        assert not CoverCompositor._validate_overlay_path("/tmp/evil.png")  # noqa: S108

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


# ---------------------------------------------------------------------------
# Fake ThemeProfile for back cover tests
# ---------------------------------------------------------------------------


@dataclass
class _FakePalette:
    base: list[str] = field(default_factory=lambda: ["#35654d"])
    accents_allowed: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)


@dataclass
class _FakePromptBlocks:
    subject: str = "test"
    environment: str = "test"
    tone: str = "test"
    positives: list[str] = field(default_factory=lambda: ["test"])
    negatives: list[str] = field(default_factory=lambda: ["test"])


@dataclass
class _FakeThemeProfile:
    """Minimal fake for ThemeProfile to test back cover overlays."""

    id: str = "test"
    label: str = "Test"
    palette: _FakePalette = field(default_factory=_FakePalette)
    blocks: _FakePromptBlocks = field(default_factory=_FakePromptBlocks)
    cover_title_image: str = ""
    cover_footer_image: str = ""
    back_cover: BackCoverConfig | None = None


def _make_back_cover_config() -> BackCoverConfig:
    """Create a test BackCoverConfig."""
    return BackCoverConfig(
        preview_pages=[0, 1],
        tagline="Test tagline for coloring!",
        description="A wonderful coloring book for kids.",
        author="Test Author",
        publisher="Test Publisher",
    )


class TestBackCoverCompositor:
    """Tests for back cover overlay composition."""

    def test_back_cover_overlays_produces_valid_image(self) -> None:
        """Test that full overlay produces a valid image of same size."""
        compositor = CoverCompositor()
        cover_size = 2626
        base = _make_png(cover_size, cover_size, "green")
        pages = [_make_png(2626, 2626, "white"), _make_png(2626, 2626, "white")]
        profile = _FakeThemeProfile(back_cover=_make_back_cover_config())

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=pages,
        )

        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (cover_size, cover_size)

    def test_back_cover_preview_images_side_by_side(self) -> None:
        """Test that 2 preview images are placed side by side in the top zone."""
        compositor = CoverCompositor()
        cover_size = 2626
        base = _make_png(cover_size, cover_size, "white")
        # Use distinct colors for each page preview
        page_red = _make_png(500, 500, "red")
        page_blue = _make_png(500, 500, "blue")
        profile = _FakeThemeProfile(back_cover=_make_back_cover_config())

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[page_red, page_blue],
        )

        result_img = Image.open(io.BytesIO(result))
        # Check left preview area has red pixels (within border offset)
        left_quarter_x = cover_size // 4
        preview_mid_y = BACK_COVER_PREVIEW_TOP_PX + 100
        left_pixel = result_img.getpixel((left_quarter_x, preview_mid_y))
        assert left_pixel[0] > 200, f"Expected red in left preview, got {left_pixel}"

        # Check right preview area has blue pixels
        right_quarter_x = 3 * cover_size // 4
        right_pixel = result_img.getpixel((right_quarter_x, preview_mid_y))
        assert right_pixel[2] > 200, f"Expected blue in right preview, got {right_pixel}"

    def test_back_cover_preview_images_rounded_corners(self) -> None:
        """Test that preview image corners are rounded (transparent at corners)."""
        compositor = CoverCompositor()
        cover_size = 2626
        base = _make_png(cover_size, cover_size, "white")
        page = _make_png(500, 500, "red")
        config = _make_back_cover_config()
        config.preview_pages = [0, 0]  # Both same page
        profile = _FakeThemeProfile(back_cover=config)

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[page],
        )

        result_img = Image.open(io.BytesIO(result))
        # The very top-left corner of the preview should still be white (rounded off)
        # Preview starts at PADDING_PX + border, BACK_COVER_PREVIEW_TOP_PX + border
        corner_pixel = result_img.getpixel((PADDING_PX, BACK_COVER_PREVIEW_TOP_PX))
        # Should be white (background), not red (preview) due to rounded corners + border
        assert corner_pixel[0] == 255 and corner_pixel[1] == 255, f"Expected white corner (rounded), got {corner_pixel}"

    def test_back_cover_tagline_centered(self) -> None:
        """Test that the tagline text is drawn centered horizontally."""
        compositor = CoverCompositor()
        cover_size = 2626
        base = _make_png(cover_size, cover_size, "white")
        profile = _FakeThemeProfile(back_cover=_make_back_cover_config())

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[_make_png(100, 100, "gray")],
        )

        result_img = Image.open(io.BytesIO(result))
        center_x = cover_size // 2
        # Scan from top (after preview zone ~200px) down to mid-cover for black text
        found_text_pixel = False
        for y in range(150, cover_size // 2):
            pixel = result_img.getpixel((center_x, y))
            if pixel[0] < 50 and pixel[1] < 50 and pixel[2] < 50:
                found_text_pixel = True
                break
        assert found_text_pixel, "Expected black text pixels in center of text zone"

    def test_back_cover_description_below_tagline(self) -> None:
        """Test that description text appears below the tagline."""
        compositor = CoverCompositor()
        cover_size = 2626
        base = _make_png(cover_size, cover_size, "white")
        profile = _FakeThemeProfile(back_cover=_make_back_cover_config())

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[_make_png(100, 100, "gray"), _make_png(100, 100, "gray")],
        )

        result_img = Image.open(io.BytesIO(result))
        # Find text clusters: scan from preview zone end to mid-cover
        center_x = cover_size // 2
        text_rows = []
        in_text = False
        for y in range(150, cover_size - 300):
            pixel = result_img.getpixel((center_x, y))
            is_dark = pixel[0] < 50 and pixel[1] < 50 and pixel[2] < 50
            if is_dark and not in_text:
                text_rows.append(y)
                in_text = True
            elif not is_dark:
                in_text = False
        # Should have at least 2 text blocks (tagline + description)
        assert len(text_rows) >= 2, f"Expected 2+ text blocks, found starts at rows: {text_rows}"

    def test_back_cover_credits_at_bottom(self) -> None:
        """Test that credits (author + publisher) are at the bottom of the cover."""
        compositor = CoverCompositor()
        cover_size = 2626
        base = _make_png(cover_size, cover_size, "white")
        profile = _FakeThemeProfile(back_cover=_make_back_cover_config())

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[_make_png(100, 100, "gray"), _make_png(100, 100, "gray")],
        )

        result_img = Image.open(io.BytesIO(result))
        center_x = cover_size // 2
        # Check credits zone: near BACK_COVER_CREDITS_BOTTOM_PX from bottom
        credits_y = cover_size - BACK_COVER_CREDITS_BOTTOM_PX
        found_credits_pixel = False
        for y in range(credits_y, min(credits_y + 100, cover_size)):
            pixel = result_img.getpixel((center_x, y))
            if pixel[0] < 50 and pixel[1] < 50 and pixel[2] < 50:
                found_credits_pixel = True
                break
        assert found_credits_pixel, "Expected credits text pixels near bottom of cover"

    def test_back_cover_text_backdrop_present(self) -> None:
        """Test that the semi-transparent backdrop is drawn behind text."""
        compositor = CoverCompositor()
        cover_size = 2626
        # Use dark green base so backdrop (white semi-transparent) is detectable
        base = _make_png(cover_size, cover_size, "darkgreen")
        profile = _FakeThemeProfile(back_cover=_make_back_cover_config())

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[_make_png(100, 100, "gray"), _make_png(100, 100, "gray")],
        )

        result_img = Image.open(io.BytesIO(result))
        center_x = cover_size // 2
        # Backdrop is behind text. With small previews, text starts ~256px.
        # Scan for a pixel that's lighter than darkgreen (0, 100, 0) due to white backdrop.
        found_lightened = False
        for y in range(200, 600):
            pixel = result_img.getpixel((center_x, y))
            # Backdrop alpha-composites white onto darkgreen → green channel > 100
            if pixel[1] > 110 and pixel[0] > 10:
                found_lightened = True
                break
        assert found_lightened, "Expected backdrop to lighten green in text zone"

    def test_back_cover_barcode_zone_clear(self) -> None:
        """Test that the barcode zone (bottom-right) is not covered by overlays."""
        compositor = CoverCompositor()
        cover_size = 2626
        base = _make_png(cover_size, cover_size, "white")
        profile = _FakeThemeProfile(back_cover=_make_back_cover_config())

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[_make_png(100, 100, "gray"), _make_png(100, 100, "gray")],
        )

        result_img = Image.open(io.BytesIO(result))
        # Barcode zone: bottom-right corner, ~15% width, ~8% height
        barcode_x = int(cover_size * 0.90)
        barcode_y = int(cover_size * 0.95)
        pixel = result_img.getpixel((barcode_x, barcode_y))
        # Should be white (unchanged)
        assert pixel[0] > 240 and pixel[1] > 240 and pixel[2] > 240, f"Expected barcode zone to be clear (white), got {pixel}"

    def test_back_cover_invalid_page_index_graceful(self) -> None:
        """Test that page indices beyond available pages are handled gracefully."""
        compositor = CoverCompositor()
        cover_size = 2626
        base = _make_png(cover_size, cover_size, "green")
        config = _make_back_cover_config()
        config.preview_pages = [99, 100]  # Way beyond available pages
        profile = _FakeThemeProfile(back_cover=config)

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[_make_png(100, 100, "red")],  # Only 1 page
        )

        # Should produce a valid image without crashing
        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (cover_size, cover_size)

    def test_back_cover_no_config_returns_unchanged(self) -> None:
        """Test that when back_cover is None, the image is returned unchanged."""
        compositor = CoverCompositor()
        base = _make_png(2626, 2626, "green")
        profile = _FakeThemeProfile(back_cover=None)

        result = compositor.apply_back_cover_overlays(
            back_cover_data=base,
            theme_profile=profile,  # type: ignore[arg-type]
            content_pages=[_make_png(100, 100, "red")],
        )

        # Should be identical bytes (no processing)
        assert result == base
