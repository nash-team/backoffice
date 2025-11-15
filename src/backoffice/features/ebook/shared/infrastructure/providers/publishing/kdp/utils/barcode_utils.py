"""KDP barcode space reservation utilities.

This module provides utilities to add white rectangle space for Amazon KDP barcodes
on back covers, following official KDP specifications.

Official KDP barcode requirements:
- Width: 2.0 inches / 50.8 mm (600px @ 300 DPI)
- Height: 1.2 inches / 30.5 mm (360px @ 300 DPI)
- Position: Bottom-right corner
- Margin: 0.25 inches from edges (75px @ 300 DPI)

Reference: https://kdp.amazon.com/help/topic/G201953020
"""

import logging
from io import BytesIO

from PIL import Image, ImageDraw

from backoffice.features.ebook.shared.domain.entities.ebook import inches_to_px

logger = logging.getLogger(__name__)


def add_barcode_space(
    image_bytes: bytes,
    barcode_width_inches: float = 2.0,
    barcode_height_inches: float = 1.2,
    barcode_margin_inches: float = 0.25,
) -> bytes:
    """Add white rectangle for KDP barcode on back cover.

    Uses exact KDP specifications from config/kdp/specifications.yaml:
    - Width: 2.0" / 50.8 mm (default)
    - Height: 1.2" / 30.5 mm (default)
    - Position: Bottom-right
    - Margin: 0.25" from edges (default)

    Args:
        image_bytes: Back cover image bytes (PNG format)
        barcode_width_inches: Barcode width in inches (default: 2.0)
        barcode_height_inches: Barcode height in inches (default: 1.2)
        barcode_margin_inches: Margin from edges in inches (default: 0.25)

    Returns:
        Image bytes with white barcode space reserved

    Raises:
        ValueError: If image format is invalid
    """
    logger.info(
        f'Adding KDP barcode space: {barcode_width_inches}" × {barcode_height_inches}" '
        f'with {barcode_margin_inches}" margin'
    )

    try:
        img = Image.open(BytesIO(image_bytes))
        draw = ImageDraw.Draw(img)

        w, h = img.size

        # Convert inches to pixels @ 300 DPI (exact KDP dimensions)
        rect_w = inches_to_px(barcode_width_inches)  # 2.0" = 600px
        rect_h = inches_to_px(barcode_height_inches)  # 1.2" = 360px
        margin = inches_to_px(barcode_margin_inches)  # 0.25" = 75px

        # Bottom-right white rectangle
        x1 = w - rect_w - margin
        y1 = h - rect_h - margin
        x2 = w - margin
        y2 = h - margin

        # Validate dimensions fit within image
        if x1 < 0 or y1 < 0:
            logger.warning(
                f"⚠️ Barcode space ({rect_w}×{rect_h}px + {margin}px margin) "
                f"too large for image ({w}×{h}px), adjusting..."
            )
            # Fallback to percentage-based if dimensions don't fit
            rect_w = min(rect_w, int(w * 0.3))
            rect_h = min(rect_h, int(h * 0.2))
            margin = min(margin, int(w * 0.02))

            x1 = max(0, w - rect_w - margin)
            y1 = max(0, h - rect_h - margin)
            x2 = w - margin
            y2 = h - margin

        draw.rectangle((x1, y1, x2, y2), fill=(255, 255, 255))

        logger.info(
            f"✅ KDP barcode space added: ({x1}, {y1}) to ({x2}, {y2}) "
            f"= {rect_w}×{rect_h}px with {margin}px margin"
        )

        # Convert back to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"❌ Failed to add barcode space: {str(e)}")
        raise ValueError(f"Failed to add barcode space: {str(e)}") from e
