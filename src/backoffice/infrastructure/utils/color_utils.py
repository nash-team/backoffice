"""Color utilities for KDP export (CMYK conversion, color extraction)."""

import colorsys
import logging
from io import BytesIO
from typing import cast

from PIL import Image, ImageCms
from PIL.Image import Image as PILImage

logger = logging.getLogger(__name__)

# ✅ CMYK black K 100% in PIL (8-bit channels: 0-255)
TEXT_BLACK_CMYK = (0, 0, 0, 255)


def convert_rgb_to_cmyk(
    image_bytes: bytes,
    icc_rgb: str = "sRGB.icc",
    icc_cmyk: str = "CoatedFOGRA39.icc",
) -> bytes:
    """Convert RGB image to CMYK with ICC profiles.

    Args:
        image_bytes: RGB image bytes
        icc_rgb: Source ICC profile (default: sRGB)
        icc_cmyk: Target CMYK profile (default: CoatedFOGRA39 for Europe)

    Returns:
        CMYK TIFF image bytes at 300 DPI

    Note:
        Falls back gracefully to PIL's built-in CMYK conversion if ICC profiles not available.
        KDP accepts RGB but CMYK is more reliable for print.
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    try:
        # ICC profile conversion
        cmyk_img = ImageCms.profileToProfile(img, icc_rgb, icc_cmyk, outputMode="CMYK")
        logger.info(f"✅ Conversion CMYK avec profil {icc_cmyk}")

        # Save as TIFF with explicit DPI
        buffer = BytesIO()
        cmyk_img.save(buffer, format="TIFF", compression="tiff_adobe_deflate", dpi=(300, 300))
        return buffer.getvalue()

    except Exception as e:
        logger.warning(f"⚠️ Conversion ICC échouée, fallback CMYK natif PIL: {e}")
        # Use PIL's built-in CMYK conversion (simpler but less accurate)
        cmyk_img = img.convert("CMYK")
        buffer = BytesIO()
        cmyk_img.save(buffer, format="TIFF", compression="tiff_adobe_deflate", dpi=(300, 300))
        return buffer.getvalue()


def extract_dominant_color_faded(image_bytes: bytes) -> tuple[int, int, int]:
    """Extract dominant color and reduce saturation for faded background effect.

    Args:
        image_bytes: Image bytes to analyze

    Returns:
        RGB tuple (r, g, b) with reduced saturation/value, clamped to [10, 245]
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    # Resize for performance
    img_small = img.resize((150, 150))
    colors = img_small.getcolors(150 * 150)

    if not colors:
        # Fallback: neutral gray
        return (200, 200, 200)

    # Most frequent color (getcolors returns tuple[int, Any], cast to RGB tuple)
    _, dominant_rgb_raw = max(colors, key=lambda x: x[0])
    dominant_rgb = cast(tuple[int, int, int], dominant_rgb_raw)

    # Convert to HSV
    r, g, b = dominant_rgb
    hsv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

    # Reduce saturation (20%) and value (15%) for faded effect
    hsv_faded = (hsv[0], hsv[1] * 0.80, hsv[2] * 0.85)

    # Convert back to RGB with clamp [10, 245]
    rgb_faded = colorsys.hsv_to_rgb(*hsv_faded)
    return cast(tuple[int, int, int], tuple(max(10, min(245, int(c * 255))) for c in rgb_faded))


def extract_dominant_color_exact(image_bytes: bytes) -> tuple[int, int, int]:
    """Extract most saturated dominant color (ignores whites/grays).

    Args:
        image_bytes: Image bytes to analyze

    Returns:
        RGB tuple (r, g, b) - most vibrant dominant color from image
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    # Resize for performance
    img_small = img.resize((150, 150))
    colors = img_small.getcolors(150 * 150)

    if not colors:
        # Fallback: sky blue
        return (135, 206, 235)

    # Filter out low-saturation colors (whites, grays, blacks)
    # and find most frequent among saturated colors
    saturated_colors: list[tuple[int, tuple[int, int, int]]] = []
    for count, rgb_color_raw in colors:
        rgb_color = cast(tuple[int, int, int], rgb_color_raw)
        r, g, b = rgb_color
        # Calculate saturation (difference between max and min channel)
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = max_val - min_val

        # Keep only colors with good saturation (>30) and not too dark/bright
        if saturation > 30 and 30 < max_val < 240:
            saturated_colors.append((count, rgb_color))

    # If we have saturated colors, pick the most frequent
    if saturated_colors:
        dominant_rgb = max(saturated_colors, key=lambda x: x[0])[1]
        return dominant_rgb

    # Fallback: return most frequent color even if not saturated
    _, fallback_rgb_raw = max(colors, key=lambda x: x[0])
    return cast(tuple[int, int, int], fallback_rgb_raw)


def extract_dominant_color_vibrant(image_bytes: bytes) -> tuple[int, int, int]:
    """Extract dominant color keeping vibrant saturation for back cover.

    Args:
        image_bytes: Image bytes to analyze

    Returns:
        RGB tuple (r, g, b) with preserved vibrant colors
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    # Resize for performance
    img_small = img.resize((150, 150))
    colors = img_small.getcolors(150 * 150)

    if not colors:
        # Fallback: sky blue
        return (135, 206, 235)

    # Most frequent color
    _, dominant_rgb_raw = max(colors, key=lambda x: x[0])
    dominant_rgb = cast(tuple[int, int, int], dominant_rgb_raw)

    # Convert to HSV to adjust slightly
    r, g, b = dominant_rgb
    hsv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

    # Keep saturation high (only reduce by 10% max) and maintain brightness
    # This gives a cohesive but still colorful back cover
    hsv_vibrant = (hsv[0], max(0.3, hsv[1] * 0.9), max(0.4, hsv[2]))

    # Convert back to RGB
    rgb_vibrant = colorsys.hsv_to_rgb(*hsv_vibrant)
    return cast(tuple[int, int, int], tuple(min(255, int(c * 255)) for c in rgb_vibrant))


def ensure_cmyk(img: PILImage, icc_cmyk: str = "CoatedFOGRA39.icc") -> PILImage:
    """Force image to CMYK mode. Use before assembly.

    Args:
        img: PIL Image in any mode
        icc_cmyk: Target CMYK profile

    Returns:
        Image in CMYK mode
    """
    if img.mode == "CMYK":
        return img

    if img.mode != "RGB":
        img = img.convert("RGB")

    try:
        result_img = ImageCms.profileToProfile(img, "sRGB.icc", icc_cmyk, outputMode="CMYK")
        return cast(PILImage, result_img)
    except Exception as e:
        logger.warning(f"⚠️ Normalisation CMYK échouée, conversion naïve: {e}")
        return img.convert("CMYK")
