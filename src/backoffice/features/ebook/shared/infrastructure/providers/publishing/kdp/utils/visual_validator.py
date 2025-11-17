"""KDP visual validation utilities.

This module provides utilities to visually validate full KDP covers (back + spine + front)
against official Amazon KDP templates by overlaying the template.
"""

import logging
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from backoffice.features.ebook.shared.domain.entities.ebook import (
    KDPExportConfig,
    calculate_spine_width,
    inches_to_px,
)
from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils import (
    barcode_utils,
)

logger = logging.getLogger(__name__)

# Path to KDP template (relative to project root)
# __file__ = .../features/ebook/shared/.../publishing/kdp/utils/visual_validator.py
# Need to go up to project root: 11 levels up from utils/
_CURRENT_FILE = Path(__file__)
_PROJECT_ROOT = _CURRENT_FILE.parent.parent.parent.parent.parent.parent.parent.parent.parent.parent.parent
KDP_TEMPLATE_PATH = _PROJECT_ROOT / "config" / "kdp" / "PAPERBACK_8.500x8.500_24_STANDARD_WHITE_fr_FR.png"


def assemble_full_kdp_cover(
    back_cover_bytes: bytes,
    front_cover_bytes: bytes,
    page_count: int = 24,
) -> bytes:
    """Assemble a complete KDP cover (back + spine + front) from individual covers.

    Follows exact KDP specifications for 8.5"×8.5" paperback with bleeds.

    Args:
        back_cover_bytes: Back cover image bytes (8.5"×8.5" @ 300 DPI)
        front_cover_bytes: Front cover image bytes (8.5"×8.5" @ 300 DPI)
        page_count: Number of pages for spine width calculation (default: 24)

    Returns:
        Full KDP cover image bytes @ 300 DPI with bleeds
        Dimensions: 17.304" × 8.75" @ 300 DPI = 5191×2625px

    Raises:
        ValueError: If image dimensions don't match requirements
    """
    config = KDPExportConfig()

    # Load covers
    back = Image.open(BytesIO(back_cover_bytes)).convert("RGB")
    front = Image.open(BytesIO(front_cover_bytes)).convert("RGB")

    # Verify dimensions (should be 2550×2550px @ 300 DPI for 8.5"×8.5")
    expected_size = (2550, 2550)
    if back.size != expected_size:
        raise ValueError(f"Back cover must be {expected_size}, got {back.size}")
    if front.size != expected_size:
        raise ValueError(f"Front cover must be {expected_size}, got {front.size}")

    # Calculate spine width in inches
    spine_width_inches = calculate_spine_width(page_count, config.paper_type)
    spine_width_px = inches_to_px(spine_width_inches)

    # Calculate full cover dimensions @ 300 DPI
    bleed_px = inches_to_px(config.bleed_size)  # 0.125" = 38px

    # ✅ KDP full cover structure (matches cover_assembly_provider.py):
    # [LEFT_BLEED][BACK_TRIM][SPINE][FRONT_TRIM][RIGHT_BLEED]
    # Total: 38 + 2550 + spine + 2550 + 38 = 5192px + spine
    full_width = bleed_px + back.width + spine_width_px + front.width + bleed_px
    full_height = bleed_px + back.height + bleed_px

    logger.info(f"Assembling full KDP cover: {full_width}×{full_height}px " f'({full_width / 300:.3f}" × {full_height / 300:.3f}" @ 300 DPI) ' f"with {spine_width_px}px spine for {page_count} pages")

    # Create blank canvas with bleeds
    canvas = Image.new("RGB", (full_width, full_height), color=(255, 255, 255))

    # ✅ Add barcode space to back cover for KDP validation preview
    # Note: Back cover from DB is raw (no barcode). We add it here to simulate
    # the final KDP export and validate positioning against the KDP template.
    logger.info("Adding KDP barcode space to back cover for validation preview...")
    back_buffer = BytesIO()
    back.save(back_buffer, format="PNG")
    back_with_barcode = barcode_utils.add_barcode_space(
        back_buffer.getvalue(),
        barcode_width_inches=config.barcode_width,
        barcode_height_inches=config.barcode_height,
        barcode_margin_inches=config.barcode_margin,
        image_includes_bleeds=False,  # Back cover is 2550×2550 (no bleeds yet)
        bleed_size_inches=config.bleed_size,
        has_right_bleed=False,  # NO right bleed - spine comes after
    )
    back = Image.open(BytesIO(back_with_barcode)).convert("RGB")

    # ✅ Paste back cover at (bleed_px, bleed_px) - creates left bleed
    canvas.paste(back, (bleed_px, bleed_px))

    # ✅ Spine position: immediately after back trim (NO gap, NO extra bleed)
    # Position: left_bleed + back_width = 38 + 2550 = 2588px
    spine_x = bleed_px + back.width
    # Draw spine color (use back cover's dominant color or white)
    spine_region = (spine_x, bleed_px, spine_x + spine_width_px, bleed_px + back.height)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(spine_region, fill=(240, 240, 240))  # Light gray for spine

    # ✅ Paste front cover: immediately after spine (NO gap, NO extra bleed)
    # Position: spine_x + spine_width = 2588 + 16 = 2604px
    front_x = spine_x + spine_width_px
    canvas.paste(front, (front_x, bleed_px))

    # Convert to bytes
    buffer = BytesIO()
    canvas.save(buffer, format="PNG")

    logger.info(f"✅ Full cover assembled: {full_width}×{full_height}px")
    return buffer.getvalue()


def overlay_kdp_template(
    full_cover_bytes: bytes,
    template_opacity: float = 0.3,
    show_measurements: bool = True,
) -> bytes:
    """Overlay official KDP template on full cover for visual validation.

    Args:
        full_cover_bytes: Full KDP cover image bytes (back+spine+front @ 300 DPI)
        template_opacity: Opacity of template overlay (0.0-1.0, default: 0.3)
        show_measurements: Add measurement annotations (default: True)

    Returns:
        Image bytes with KDP template overlay for visual validation

    Raises:
        ValueError: If template file not found or image format invalid
    """
    if not KDP_TEMPLATE_PATH.exists():
        raise ValueError(f"KDP template not found at: {KDP_TEMPLATE_PATH}")

    logger.info(f"📐 Overlaying KDP template with {template_opacity:.0%} opacity")

    try:
        # Load full cover @ 300 DPI
        cover_img = Image.open(BytesIO(full_cover_bytes)).convert("RGBA")
        w, h = cover_img.size

        # Load KDP template @ 600 DPI (10383×5250px)
        template_full = Image.open(KDP_TEMPLATE_PATH).convert("RGBA")
        template_w, template_h = template_full.size

        # Resize template from 600 DPI to 300 DPI (÷2)
        template_300 = template_full.resize((template_w // 2, template_h // 2), Image.Resampling.LANCZOS)

        # Verify dimensions match after resize
        if cover_img.size != template_300.size:
            cover_size = cover_img.size
            template_size = template_300.size
            logger.warning(f"⚠️ Size mismatch after resize: Cover={cover_size}, Template={template_size}")
            # Resize template to exactly match cover
            template_300 = template_300.resize(cover_img.size, Image.Resampling.LANCZOS)

        logger.info(f"✂️ Template resized: {template_w}×{template_h}px @ 600 DPI → " f"{template_300.size[0]}×{template_300.size[1]}px @ 300 DPI")

        # Adjust template opacity
        alpha = template_300.split()[3]
        alpha = alpha.point(lambda p: int(p * template_opacity))
        template_300.putalpha(alpha)

        # Composite images
        result = Image.alpha_composite(cover_img, template_300)

        # Add measurement annotations if requested
        if show_measurements:
            result = _add_measurement_annotations(result)

        # Convert back to RGB for PNG output
        result_rgb = result.convert("RGB")

        # Save to bytes
        buffer = BytesIO()
        result_rgb.save(buffer, format="PNG")

        logger.info(f"✅ KDP template overlay complete: {w}×{h}px")
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"❌ Failed to overlay KDP template: {str(e)}")
        raise ValueError(f"Failed to overlay KDP template: {str(e)}") from e


def _add_measurement_annotations(img: Image.Image) -> Image.Image:
    """Add measurement annotations to validation image.

    Args:
        img: Image to annotate (full cover)

    Returns:
        Annotated image
    """
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Try to use a nice font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    except OSError as e:
        logger.warning(f"Font not found, using default: {e}")
        font = ImageFont.load_default()  # type: ignore[assignment]
        font_small = font

    # Text color with outline for visibility
    text_color = (255, 0, 0, 255)  # Red
    outline_color = (255, 255, 255, 200)  # White

    # Add dimension labels
    annotations = [
        # Top-left: full cover dimensions
        (50, 50, f'{w}×{h}px ({w / 300:.3f}"×{h / 300:.3f}" @ 300 DPI)', font),
        # Bottom-left: barcode info
        (50, h - 100, 'Barcode: 2.0"×1.2" (600×360px)', font_small),
        (50, h - 60, 'Margin: 0.25" (75px)', font_small),
    ]

    for x, y, text, text_font in annotations:
        # Draw outline
        for offset_x in [-2, 0, 2]:
            for offset_y in [-2, 0, 2]:
                if offset_x != 0 or offset_y != 0:
                    draw.text((x + offset_x, y + offset_y), text, font=text_font, fill=outline_color)
        # Draw text
        draw.text((x, y), text, font=text_font, fill=text_color)

    return img


def validate_full_cover_against_template(
    full_cover_bytes: bytes,
) -> dict[str, bool | str | tuple[int, int]]:
    """Validate a full KDP cover against template dimensions.

    Args:
        full_cover_bytes: Full cover image bytes (back+spine+front)

    Returns:
        Validation results with boolean checks and messages
    """
    if not KDP_TEMPLATE_PATH.exists():
        return {
            "valid": False,
            "message": f"KDP template not found at: {KDP_TEMPLATE_PATH}",
        }

    try:
        # Load images
        cover_img = Image.open(BytesIO(full_cover_bytes))
        template_img = Image.open(KDP_TEMPLATE_PATH)

        cover_size = cover_img.size
        template_size = template_img.size

        # Expected size @ 300 DPI: template @ 600 DPI ÷ 2
        expected_size = (template_size[0] // 2, template_size[1] // 2)
        size_correct = cover_size == expected_size

        expected_w, expected_h = expected_size
        success_msg = f"✅ Full cover matches KDP template dimensions ({expected_w}×{expected_h}px @ 300 DPI)"
        error_msg = f"❌ Size mismatch: {cover_size} vs expected {expected_size}"

        result: dict[str, bool | str | tuple[int, int]] = {
            "valid": size_correct,
            "cover_size": cover_size,
            "template_size": template_size,
            "expected_size": expected_size,
            "size_correct": size_correct,
            "message": success_msg if size_correct else error_msg,
        }

        logger.info(f"Validation result: {result['message']}")
        return result

    except Exception as e:
        logger.error(f"❌ Validation failed: {str(e)}")
        return {
            "valid": False,
            "message": f"Validation error: {str(e)}",
        }
