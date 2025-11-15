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


def remove_barcode_space_for_preview(
    image_bytes: bytes,
    barcode_width_inches: float = 2.0,
    barcode_height_inches: float = 1.2,
    barcode_margin_inches: float = 0.25,
) -> bytes:
    """Remove white barcode rectangle from back cover for visual preview.

    This function is used to restore the original design under the barcode space
    for KDP cover previews where we want to see the full design with the template overlay.

    Note: This doesn't restore the original content - it just fills the white rectangle
    with a neutral color or makes it transparent. The KDP template overlay will show
    where the barcode will be positioned.

    Args:
        image_bytes: Back cover image bytes with barcode space (PNG format)
        barcode_width_inches: Barcode width in inches (default: 2.0)
        barcode_height_inches: Barcode height in inches (default: 1.2)
        barcode_margin_inches: Margin from edges in inches (default: 0.25)

    Returns:
        Image bytes with barcode space removed (transparent or filled with design color)
    """
    # For now, just return the original image
    # The white rectangle will stay, but the KDP template overlay will show where it should be
    # TODO: Could implement content-aware fill or transparency if needed
    return image_bytes


def add_barcode_space(
    image_bytes: bytes,
    barcode_width_inches: float = 2.0,
    barcode_height_inches: float = 1.2,
    barcode_margin_inches: float = 0.25,
    image_includes_bleeds: bool = False,
    bleed_size_inches: float = 0.125,
    has_right_bleed: bool = False,
) -> bytes:
    """Add white rectangle for KDP barcode on back cover.

    Uses exact KDP specifications from config/kdp/specifications.yaml:
    - Width: 2.0" / 50.8 mm (default)
    - Height: 1.2" / 30.5 mm (default)
    - Position: Bottom-right
    - Margin: 0.25" from TRIM edges (default)

    IMPORTANT: The margin is always measured from the TRIM edges (cut lines),
    not from the image edges.

    For KDP back covers in full cover assembly:
    - Image has LEFT bleed (38px) + trim (2550px) = 2588px width
    - NO right bleed (spine comes right after)
    - So right edge of image = right edge of trim
    - Barcode should be margin_from_trim (75px) from right edge of IMAGE

    Args:
        image_bytes: Back cover image bytes (PNG format)
        barcode_width_inches: Barcode width in inches (default: 2.0)
        barcode_height_inches: Barcode height in inches (default: 1.2)
        barcode_margin_inches: Margin from TRIM edges in inches (default: 0.25)
        image_includes_bleeds: Whether image already includes bleeds (default: False)
        bleed_size_inches: Bleed size in inches if included (default: 0.125)
        has_right_bleed: Whether image has bleed on right edge (default: False)
                        For KDP back covers, this is False (spine comes after)

    Returns:
        Image bytes with white barcode space reserved

    Raises:
        ValueError: If image format is invalid
    """
    logger.warning(
        f'📦 DEBUG: Adding KDP barcode space: {barcode_width_inches}" × {barcode_height_inches}" '
        f'with {barcode_margin_inches}" margin from trim edges'
    )

    try:
        img = Image.open(BytesIO(image_bytes))
        draw = ImageDraw.Draw(img)

        w, h = img.size

        logger.warning(f"   Image size: {w}×{h}px")
        logger.warning(
            f"   Image includes bleeds: {image_includes_bleeds} "
            f'(bleed: {bleed_size_inches}", right bleed: {has_right_bleed})'
        )

        # Convert inches to pixels @ 300 DPI (exact KDP dimensions)
        rect_w = inches_to_px(barcode_width_inches)  # 2.0" = 600px
        rect_h = inches_to_px(barcode_height_inches)  # 1.2" = 360px
        margin_from_trim = inches_to_px(barcode_margin_inches)  # 0.25" = 75px

        # ✅ Position barcode based on trim edges
        if image_includes_bleeds:
            bleed_px = inches_to_px(bleed_size_inches)  # 0.125" = 38px

            # For KDP back covers: [left_bleed(38)][trim(2550)][NO right bleed]
            # Right edge of image = right edge of trim
            # Barcode should be margin_from_trim from right trim edge
            if has_right_bleed:
                # Standard case: bleeds on both sides
                x1 = w - bleed_px - margin_from_trim - rect_w
                x2 = w - bleed_px - margin_from_trim
            else:
                # KDP back cover case: NO right bleed, spine comes after
                # Right edge of image = right edge of trim
                x1 = w - margin_from_trim - rect_w
                x2 = w - margin_from_trim

            # Bottom: always has bleed
            y1 = h - bleed_px - margin_from_trim - rect_h
            y2 = h - bleed_px - margin_from_trim

            logger.warning(
                f"   Barcode positioned at {margin_from_trim}px from right trim edge "
                f"(right bleed: {'Yes' if has_right_bleed else 'No - spine follows'})"
            )
        else:
            # No bleeds: image edge = trim edge
            x1 = w - rect_w - margin_from_trim
            y1 = h - rect_h - margin_from_trim
            x2 = w - margin_from_trim
            y2 = h - margin_from_trim

        # Validate dimensions fit within image
        if x1 < 0 or y1 < 0:
            logger.warning(
                f"⚠️ Barcode space ({rect_w}×{rect_h}px + {margin_from_trim}px margin) "
                f"too large for image ({w}×{h}px), adjusting..."
            )
            # Fallback to percentage-based if dimensions don't fit
            rect_w = min(rect_w, int(w * 0.3))
            rect_h = min(rect_h, int(h * 0.2))
            margin_from_trim = min(margin_from_trim, int(w * 0.02))

            # Recalculate with adjusted dimensions
            if image_includes_bleeds:
                bleed_px = inches_to_px(bleed_size_inches)
                if has_right_bleed:
                    x1 = max(0, w - bleed_px - margin_from_trim - rect_w)
                    x2 = w - bleed_px - margin_from_trim
                else:
                    x1 = max(0, w - margin_from_trim - rect_w)
                    x2 = w - margin_from_trim
                y1 = max(0, h - bleed_px - margin_from_trim - rect_h)
                y2 = h - bleed_px - margin_from_trim
            else:
                x1 = max(0, w - rect_w - margin_from_trim)
                y1 = max(0, h - rect_h - margin_from_trim)
                x2 = w - margin_from_trim
                y2 = h - margin_from_trim

        logger.warning(f"   Barcode rectangle position: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
        logger.warning(f"   Barcode size: {rect_w}×{rect_h}px with {margin_from_trim}px margin")
        logger.warning(f"   Calculation: x1 = {w} - {rect_w} - {margin_from_trim} = {x1}")

        draw.rectangle((x1, y1, x2, y2), fill=(255, 255, 255))

        logger.warning("✅ KDP barcode space added successfully")

        # Convert back to bytes using PNG (RGB mode for KDP)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"❌ Failed to add barcode space: {str(e)}")
        raise ValueError(f"Failed to add barcode space: {str(e)}") from e
