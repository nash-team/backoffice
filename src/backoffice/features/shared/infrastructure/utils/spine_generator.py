"""Spine (tranche) generation for KDP paperback covers."""

import logging
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as PILImage
from PIL.ImageFont import FreeTypeFont

from backoffice.features.shared.domain.entities.ebook import (
    MIN_SPINE_MARGIN,
    can_have_spine_text,
    inches_to_px,
)
from backoffice.features.shared.infrastructure.utils.color_utils import (
    ensure_cmyk,
    extract_dominant_color_faded,
)

logger = logging.getLogger(__name__)


def get_font_path(font_name: str) -> str:
    """Get absolute path to font file.

    Args:
        font_name: Name of the font file (e.g., 'PlayfairDisplay-Bold.ttf')

    Returns:
        Absolute path to font file
    """
    # Navigate to features/shared/presentation/static/fonts
    current_file = Path(__file__)
    fonts_dir = (
        current_file.parent.parent.parent
        / "features"
        / "shared"
        / "presentation"
        / "static"
        / "fonts"
    )
    return str(fonts_dir / font_name)


def load_font_safe(font_path: str, size: int, fallback: str = "DejaVuSans.ttf") -> FreeTypeFont:
    """Load font with defensive fallback.

    Args:
        font_path: Path to TTF font
        size: Font size in points
        fallback: Fallback font if primary fails

    Returns:
        ImageFont object
    """
    try:
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        logger.warning(f"⚠️ Police {font_path} non trouvée, fallback {fallback}: {e}")
        try:
            return ImageFont.truetype(fallback, size)
        except Exception:
            # Ultimate fallback: default PIL font
            default_font: FreeTypeFont = ImageFont.load_default()  # type: ignore[assignment]
            return default_font


def generate_spine(
    front_cover_bytes: bytes,
    spine_width_px: int,
    spine_height_px: int,  # trim_height + 2*bleed
    page_count: int,
    paper_type: str,
    title: str,
    author: str,
    icc_cmyk_profile: str = "CoatedFOGRA39.icc",
) -> bytes:
    """Generate spine in CMYK.

    Args:
        front_cover_bytes: Front cover for dominant color extraction
        spine_width_px: Spine width in pixels
        spine_height_px: Spine height in pixels (includes bleed top/bottom)
        page_count: Number of pages (for text eligibility)
        paper_type: Paper type for spine width calculation
        title: Book title
        author: Author name
        icc_cmyk_profile: CMYK ICC profile

    Returns:
        CMYK TIFF spine image bytes at 300 DPI
    """
    can_text, reason = can_have_spine_text(page_count, paper_type)

    if can_text:
        if reason:  # Borderline warning
            logger.warning(reason)
        spine_img = create_spine_with_text(spine_width_px, spine_height_px, title, author)
    else:
        logger.info(f"Tranche sans texte: {reason}")
        # Gradient from front cover dominant color
        dominant = extract_dominant_color_faded(front_cover_bytes)
        spine_img = create_gradient(dominant, spine_width_px, spine_height_px)

    # Normalize to CMYK
    spine_cmyk = ensure_cmyk(spine_img, icc_cmyk_profile)

    buffer = BytesIO()
    spine_cmyk.save(buffer, format="TIFF", compression="tiff_adobe_deflate", dpi=(300, 300))
    return buffer.getvalue()


def create_spine_with_text(width: int, height: int, title: str, author: str) -> PILImage:
    """Create spine with vertical text.

    Args:
        width: Spine width in pixels
        height: Spine height in pixels (trim + 2*bleed)
        title: Book title
        author: Author name

    Returns:
        RGB image (will be converted to CMYK later)
    """
    font = load_font_safe(get_font_path("PlayfairDisplay-Bold.ttf"), 24)

    # Create text on horizontal image, then rotate 90°
    temp_text = f"{title}  •  {author}"
    temp_img = Image.new("RGB", (height, width), (255, 255, 255))
    temp_draw = ImageDraw.Draw(temp_img)

    bbox = temp_draw.textbbox((0, 0), temp_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (height - text_width) // 2
    y = (width - text_height) // 2

    # ✅ Validate margins (0.0625" top/bottom)
    min_margin_px = inches_to_px(MIN_SPINE_MARGIN)
    if y < min_margin_px:
        logger.error(f"Texte spine trop proche du bord haut: y={y}, min={min_margin_px}")
        raise ValueError("Texte spine trop proche du bord haut")

    if (width - (y + text_height)) < min_margin_px:
        bottom_margin = width - (y + text_height)
        logger.error(
            f"Texte spine trop proche du bord bas: "
            f"bottom_margin={bottom_margin}, min={min_margin_px}"
        )
        raise ValueError("Texte spine trop proche du bord bas")

    temp_draw.text((x, y), temp_text, fill=(0, 0, 0), font=font)

    # Rotate -90° (clockwise)
    return temp_img.rotate(-90, expand=True)


def create_gradient(color_rgb: tuple[int, int, int], width: int, height: int) -> PILImage:
    """Create vertical gradient from color to lighter tone.

    Args:
        color_rgb: Base color (r, g, b)
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        RGB image with gradient
    """
    img = Image.new("RGB", (width, height))

    for y in range(height):
        ratio = y / height
        # Gradient towards white
        r = int(color_rgb[0] + (255 - color_rgb[0]) * ratio)
        g = int(color_rgb[1] + (255 - color_rgb[1]) * ratio)
        b = int(color_rgb[2] + (255 - color_rgb[2]) * ratio)

        for x in range(width):
            img.putpixel((x, y), (r, g, b))

    return img
