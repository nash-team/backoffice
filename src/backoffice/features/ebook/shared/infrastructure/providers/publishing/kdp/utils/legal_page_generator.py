"""Legal/copyright page generation for KDP interior."""

import logging
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

logger = logging.getLogger(__name__)

# Font settings
_TITLE_FONT_SIZE = 48
_BODY_FONT_SIZE = 24
_LINE_SPACING = 16


def _load_font(font_path: Path, size: int) -> FreeTypeFont:
    """Load font with fallback to default."""
    try:
        return ImageFont.truetype(str(font_path), size)
    except OSError as e:
        logger.warning(f"Font {font_path} not found, using default: {e}")
        return cast(FreeTypeFont, ImageFont.load_default(size=size))


def generate_legal_page(
    title: str,
    isbn: str | None,
    legal_config: dict[str, Any],
    page_width_px: int,
    page_height_px: int,
    font_dir: Path,
) -> bytes:
    """Generate a legal/copyright page as PNG bytes.

    Args:
        title: Book title (displayed at top)
        isbn: ISBN-13 string or None (omitted if None)
        legal_config: Parsed legal.yaml config dict
        page_width_px: Page width in pixels (with bleed)
        page_height_px: Page height in pixels (with bleed)
        font_dir: Path to directory containing Poppins font files

    Returns:
        PNG bytes (RGB, 300 DPI)
    """
    img = Image.new("RGB", (page_width_px, page_height_px), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(font_dir / "Poppins-Bold.ttf", _TITLE_FONT_SIZE)
    body_font = _load_font(font_dir / "Poppins-Regular.ttf", _BODY_FONT_SIZE)

    # --- Title at top (centered, ~15% from top) ---
    title_y = int(page_height_px * 0.15)
    _draw_centered_text(draw, title, title_font, page_width_px, title_y)

    # --- Legal block at bottom (centered, ~55% from top) ---
    legal_lines = _build_legal_lines(legal_config, isbn)
    block_y = int(page_height_px * 0.55)

    for line in legal_lines:
        _draw_centered_text(draw, line, body_font, page_width_px, block_y)
        bbox = draw.textbbox((0, 0), line or " ", font=body_font)
        line_height = bbox[3] - bbox[1]
        block_y += line_height + _LINE_SPACING

    buffer = BytesIO()
    img.save(buffer, format="PNG", dpi=(300, 300))
    return buffer.getvalue()


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: FreeTypeFont,
    page_width: int,
    y: int,
) -> None:
    """Draw horizontally centered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (page_width - text_width) // 2
    draw.text((x, y), text, fill=(0, 0, 0), font=font)


def _build_legal_lines(legal_config: dict[str, Any], isbn: str | None) -> list[str]:
    """Build the list of legal text lines from config."""
    copyright_cfg = legal_config["copyright"]
    publisher_cfg = legal_config["publisher"]
    printing_cfg = legal_config["printing"]

    lines = [
        f"\u00a9 {copyright_cfg['year']} {copyright_cfg['author']}. {copyright_cfg['rights']}.",
        "",
        f"\u00c9dit\u00e9 par {publisher_cfg['name']}",
        publisher_cfg["address"],
    ]

    if isbn:
        lines += ["", f"ISBN {isbn}"]

    lines += [
        "",
        f"Imprim\u00e9 en {printing_cfg['country']}",
        "",
        f"D\u00e9p\u00f4t l\u00e9gal : {legal_config['legal_deposit']}",
    ]

    return lines
