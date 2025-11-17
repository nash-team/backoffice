"""Shared image border utilities for all image providers."""

import logging
from io import BytesIO

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def add_rounded_border_to_image(
    image_bytes: bytes,
    border_width: int = 5,
    corner_radius: int = 20,
    margin: int = 50,
) -> bytes:
    """Add a rounded black border to the image with white margin.

    This utility is used by all image providers (Gemini, OpenRouter, LocalSD)
    to add consistent borders to generated images.

    Args:
        image_bytes: Original image bytes
        border_width: Width of the border in pixels (default: 5px)
        corner_radius: Radius for rounded corners in pixels (default: 20px)
        margin: White space between content and border in pixels (default: 50px)

    Returns:
        Image bytes with border and margin added

    Example:
        >>> from backoffice.features.ebook.shared.infrastructure.utils.image_borders import (
        ...     add_rounded_border_to_image,
        ... )
        >>> bordered_image = add_rounded_border_to_image(original_bytes, margin=30)
    """
    # Load image
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    orig_width, orig_height = img.size

    # Skip if image too small
    if orig_width < 100 or orig_height < 100:
        logger.warning(f"Image too small ({orig_width}x{orig_height}) for border, skipping")
        return image_bytes

    # Calculate new dimensions with margin
    total_padding = margin * 2
    new_width = orig_width
    new_height = orig_height

    # Create white background with padding
    bordered_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))

    # Shrink original image to leave margin
    content_width = new_width - total_padding
    content_height = new_height - total_padding
    img_resized = img.resize((content_width, content_height), Image.Resampling.LANCZOS)

    # Paste resized image centered with margin
    bordered_img.paste(img_resized, (margin, margin))

    # Draw the black rounded rectangle border
    draw = ImageDraw.Draw(bordered_img)
    draw.rounded_rectangle(
        (
            margin - border_width // 2,
            margin - border_width // 2,
            new_width - margin + border_width // 2 - 1,
            new_height - margin + border_width // 2 - 1,
        ),
        radius=corner_radius,
        outline=(0, 0, 0),
        width=border_width,
    )

    # Save and return
    buffer = BytesIO()
    bordered_img.save(buffer, format="PNG")
    return buffer.getvalue()
