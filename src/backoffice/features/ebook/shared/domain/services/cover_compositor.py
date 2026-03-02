"""Service for compositing title and footer images onto a generated cover."""

from __future__ import annotations

import io
import logging
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from backoffice.features.ebook.shared.domain.entities.theme_profile import ThemeProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Overlay placement constants (KDP print-safe)
# ---------------------------------------------------------------------------
#
# Amazon KDP trims covers after printing. Two zones matter:
#
#   1. Bleed (0.125" = 38px @300DPI) — will be CUT OFF, never visible.
#   2. Safe zone (0.25" = 75px @300DPI) — may shift slightly during trim.
#
# Minimum safe distance from image edge = bleed + safe zone = 0.375" ≈ 113px.
# Minimum *text* distance from trim line = 0.125" (KDP spec) → 76px from edge.
#
# HOW TO ADJUST SPACING:
#   - To move the TITLE up/down    → change PADDING_PX  (lower = closer to top)
#   - To move the FOOTER up/down   → change FOOTER_BOTTOM_PADDING_PX (lower = closer to bottom)
#   - To limit overlay HEIGHT      → change TITLE/FOOTER_MAX_HEIGHT_RATIO
#   - Hard minimum for any value   → 76px (below that, content enters the bleed zone)
#
# After changing, run:
#   python scripts/verify_cover_overlay.py --theme dinosaurs
# to visually confirm the placement.
# ---------------------------------------------------------------------------

KDP_SAFE_ZONE_INCHES = 0.25
KDP_BLEED_INCHES = 0.125
# COVER_DPI = 300
COVER_DPI = 120

PADDING_PX = 90  # title distance from top edge (76px minimum)
FOOTER_BOTTOM_PADDING_PX = 76  # footer distance from bottom edge (76px minimum)

TITLE_MAX_HEIGHT_RATIO = 0.25  # title occupies at most 25% of cover height
FOOTER_MAX_HEIGHT_RATIO = 0.1  # footer occupies at most 10% of cover height

# ---------------------------------------------------------------------------
# Back cover overlay constants
# ---------------------------------------------------------------------------
BACK_COVER_PREVIEW_TOP_PX = 90  # distance from top for preview images
BACK_COVER_PREVIEW_HEIGHT_RATIO = 0.30  # preview zone = 30% of cover height
BACK_COVER_PREVIEW_GAP_PX = 40  # gap between the 2 preview images
BACK_COVER_PREVIEW_BORDER_PX = 3  # border thickness for preview images
BACK_COVER_PREVIEW_BORDER_RADIUS_PX = 20  # corner radius for preview images
BACK_COVER_TEXT_TOP_MARGIN_PX = 60  # gap between previews and text zone
BACK_COVER_CREDITS_BOTTOM_PX = 200  # distance from bottom for credits (above barcode zone)
BACK_COVER_FONT_DIR = "config/branding/fonts"
# BACK_COVER_TAGLINE_FONT_SIZE = 60
BACK_COVER_TAGLINE_FONT_SIZE = 28
# BACK_COVER_DESCRIPTION_FONT_SIZE = 40
BACK_COVER_DESCRIPTION_FONT_SIZE = 20
BACK_COVER_CREDITS_FONT_SIZE = 36
BACK_COVER_TEXT_LINE_SPACING = 12  # extra pixels between lines

# Semi-transparent backdrop for text readability
BACK_COVER_TEXT_BACKDROP_COLOR = (255, 255, 255, 180)  # white, 70% opacity
BACK_COVER_TEXT_BACKDROP_PADDING_PX = 30

# Barcode zone dimensions (must match barcode_utils KDP specs)
BACK_COVER_BARCODE_WIDTH_INCHES = 2.0
BACK_COVER_BARCODE_HEIGHT_INCHES = 1.2
BACK_COVER_BARCODE_MARGIN_PX = 75  # 0.25" @ 300 DPI


# Allowed base directories for overlay images (relative to project root)
_ALLOWED_OVERLAY_PREFIXES = ("config/branding/",)


class CoverCompositor:
    """Composites title and footer PNG overlays onto a generated cover image."""

    @staticmethod
    def _validate_overlay_path(image_path: str) -> bool:
        """Validate that an overlay path is safe (no path traversal).

        Only paths under allowed prefixes are accepted. This prevents
        reading arbitrary files if theme YAMLs become user-editable.

        Args:
            image_path: Path string to validate

        Returns:
            True if path is safe, False otherwise
        """
        if not image_path:
            return False

        # Reject path traversal attempts
        if ".." in str(Path(image_path)):
            logger.warning(f"Rejected overlay path (traversal attempt): {image_path}")
            return False

        # Must start with an allowed prefix
        for prefix in _ALLOWED_OVERLAY_PREFIXES:
            if image_path.startswith(prefix):
                return True

        logger.warning(f"Rejected overlay path (not in allowed directory): {image_path}")
        return False

    def apply_cover_overlays(
        self,
        cover_data: bytes,
        theme_profile: ThemeProfile,
    ) -> bytes:
        """Apply title and footer overlays from theme profile onto cover data.

        Convenience method that checks if overlays are configured and applies them.
        Use this instead of duplicating the check-and-compose pattern.

        Args:
            cover_data: Raw bytes of the generated cover image
            theme_profile: Theme profile with cover_title_image and cover_footer_image

        Returns:
            Cover data with overlays applied, or original data if no overlays configured
        """
        if not theme_profile.cover_title_image and not theme_profile.cover_footer_image:
            return cover_data

        return self.compose_cover(
            base_cover=cover_data,
            title_image_path=theme_profile.cover_title_image,
            footer_image_path=theme_profile.cover_footer_image,
        )

    def compose_cover(
        self,
        base_cover: bytes,
        title_image_path: str,
        footer_image_path: str,
    ) -> bytes:
        """Compose a cover by overlaying title and footer images.

        Args:
            base_cover: Raw bytes of the base cover image (generated by Flux 2)
            title_image_path: Path to title PNG (transparent background), relative to project root
            footer_image_path: Path to footer PNG (transparent background), relative to project root

        Returns:
            Composed cover image as PNG bytes
        """
        base = Image.open(io.BytesIO(base_cover)).convert("RGBA")
        cover_width, cover_height = base.size

        logger.info(f"Compositing cover: {cover_width}x{cover_height}, padding={PADDING_PX}px (safe zone + bleed)")

        # Max width for overlays: cover width minus padding on each side
        max_overlay_width = cover_width - (2 * PADDING_PX)
        max_title_height = int(cover_height * TITLE_MAX_HEIGHT_RATIO)
        max_footer_height = int(cover_height * FOOTER_MAX_HEIGHT_RATIO)

        # Overlay title (top, centered)
        if self._validate_overlay_path(title_image_path):
            title_path = Path(title_image_path)
            if title_path.exists():
                title_img = Image.open(title_path).convert("RGBA")
                title_img = self._fit_dimensions(title_img, max_overlay_width, max_title_height)

                x = (cover_width - title_img.width) // 2
                y = PADDING_PX
                base.paste(title_img, (x, y), title_img)
                logger.info(f"Title overlaid at ({x}, {y}), size={title_img.size}")
            else:
                logger.warning(f"Title image not found: {title_path}, skipping overlay")

        # Overlay footer (bottom, centered)
        if self._validate_overlay_path(footer_image_path):
            footer_path = Path(footer_image_path)
            if footer_path.exists():
                footer_img = Image.open(footer_path).convert("RGBA")
                footer_img = self._fit_dimensions(footer_img, max_overlay_width, max_footer_height)

                x = (cover_width - footer_img.width) // 2
                y = cover_height - FOOTER_BOTTOM_PADDING_PX - footer_img.height
                base.paste(footer_img, (x, y), footer_img)
                logger.info(f"Footer overlaid at ({x}, {y}), size={footer_img.size}")
            else:
                logger.warning(f"Footer image not found: {footer_path}, skipping overlay")

        # Convert back to PNG bytes
        output = io.BytesIO()
        base.save(output, format="PNG")
        return output.getvalue()

    @staticmethod
    def _fit_dimensions(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Resize image proportionally to fit within max_width and max_height.

        Uses the most constraining dimension to maintain aspect ratio.

        Args:
            image: PIL Image to resize
            max_width: Maximum allowed width in pixels
            max_height: Maximum allowed height in pixels

        Returns:
            Resized image (or original if already fits)
        """
        if image.width <= max_width and image.height <= max_height:
            return image

        ratio = min(max_width / image.width, max_height / image.height)
        new_width = int(image.width * ratio)
        new_height = int(image.height * ratio)
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # ------------------------------------------------------------------
    # Back cover overlays
    # ------------------------------------------------------------------

    def apply_back_cover_overlays(
        self,
        back_cover_data: bytes,
        theme_profile: ThemeProfile,
        content_pages: list[bytes],
    ) -> bytes:
        """Apply preview images, promotional text and credits onto the back cover.

        Args:
            back_cover_data: Raw bytes of the back cover image (after text removal)
            theme_profile: Theme profile with optional back_cover config
            content_pages: List of content page image bytes (for preview extraction)

        Returns:
            Back cover with overlays applied, or original data if no config
        """
        if not theme_profile.back_cover:
            return back_cover_data

        config = theme_profile.back_cover
        base = Image.open(io.BytesIO(back_cover_data)).convert("RGBA")
        cover_width, cover_height = base.size

        logger.info(f"Compositing back cover: {cover_width}x{cover_height}, previews={config.preview_pages}")

        # Load fonts
        tagline_font = self._load_font("Poppins-Bold.ttf", BACK_COVER_TAGLINE_FONT_SIZE)
        desc_font = self._load_font("Poppins-Regular.ttf", BACK_COVER_DESCRIPTION_FONT_SIZE)
        credits_font = self._load_font("Poppins-Regular.ttf", BACK_COVER_CREDITS_FONT_SIZE)

        # --- Zone 1: Preview images (top) ---
        max_preview_height = int(cover_height * BACK_COVER_PREVIEW_HEIGHT_RATIO)
        preview_y_end = self._draw_preview_images(
            base,
            content_pages,
            config.preview_pages,
            cover_width,
            max_preview_height,
        )

        # --- Zone 2: Text (middle) — tagline + description ---
        text_max_width = cover_width - (2 * PADDING_PX)
        text_y_start = preview_y_end + BACK_COVER_TEXT_TOP_MARGIN_PX

        # Calculate text block height for backdrop
        tagline_height = self._measure_text_block_height(
            config.tagline,
            tagline_font,
            text_max_width,
        )
        desc_height = self._measure_text_block_height(
            config.description,
            desc_font,
            text_max_width,
        )
        total_text_height = tagline_height + BACK_COVER_TEXT_LINE_SPACING * 2 + desc_height

        # Draw semi-transparent backdrop behind text
        backdrop = Image.new("RGBA", base.size, (0, 0, 0, 0))
        backdrop_draw = ImageDraw.Draw(backdrop)
        pad = BACK_COVER_TEXT_BACKDROP_PADDING_PX
        backdrop_draw.rounded_rectangle(
            (
                PADDING_PX - pad,
                text_y_start - pad,
                cover_width - PADDING_PX + pad,
                text_y_start + total_text_height + pad,
            ),
            radius=BACK_COVER_PREVIEW_BORDER_RADIUS_PX,
            fill=BACK_COVER_TEXT_BACKDROP_COLOR,
        )
        base = Image.alpha_composite(base, backdrop)

        draw = ImageDraw.Draw(base)

        # Draw tagline
        current_y = self._draw_text_centered(
            draw,
            config.tagline,
            text_y_start,
            tagline_font,
            fill=(0, 0, 0, 255),
            max_width=text_max_width,
            cover_width=cover_width,
        )

        current_y += BACK_COVER_TEXT_LINE_SPACING * 2

        # Draw description
        self._draw_text_centered(
            draw,
            config.description,
            current_y,
            desc_font,
            fill=(0, 0, 0, 255),
            max_width=text_max_width,
            cover_width=cover_width,
        )

        # --- Zone 3: Credits (bottom) ---
        credits_y = cover_height - BACK_COVER_CREDITS_BOTTOM_PX
        author_text = f"Auteur : {config.author}"
        publisher_text = f"Editions : {config.publisher}"

        self._draw_text_left(
            draw,
            author_text,
            credits_y,
            credits_font,
            fill=(0, 0, 0, 255),
            max_width=text_max_width,
            cover_width=cover_width,
        )
        credits_y += self._get_font_line_height(credits_font) + BACK_COVER_TEXT_LINE_SPACING
        self._draw_text_left(
            draw,
            publisher_text,
            credits_y,
            credits_font,
            fill=(0, 0, 0, 255),
            max_width=text_max_width,
            cover_width=cover_width,
        )

        # --- Zone 4: Barcode (bottom-right, optional) ---
        if config.isbn:
            self._draw_barcode(base, config.isbn, cover_width, cover_height)

        output = io.BytesIO()
        base.save(output, format="PNG")
        logger.info("Back cover overlays applied successfully")
        return output.getvalue()

    def _draw_preview_images(
        self,
        base: Image.Image,
        content_pages: list[bytes],
        preview_pages: list[int],
        cover_width: int,
        max_preview_height: int,
    ) -> int:
        """Draw 2 preview images side by side at the top of the back cover.

        Args:
            base: Base image to draw on (modified in place)
            content_pages: All content page bytes
            preview_pages: Indices of pages to preview (0-based into content_pages)
            cover_width: Cover width in pixels
            max_preview_height: Maximum height for preview zone

        Returns:
            Y coordinate of the bottom edge of the preview zone
        """
        preview_images: list[Image.Image] = []
        for page_idx in preview_pages:
            if page_idx < len(content_pages):
                img = Image.open(io.BytesIO(content_pages[page_idx])).convert("RGBA")
                preview_images.append(img)
            else:
                logger.warning(f"Preview page index {page_idx} out of range (only {len(content_pages)} pages), skipping")

        if not preview_images:
            return BACK_COVER_PREVIEW_TOP_PX

        # Calculate available width for each preview
        usable_width = cover_width - (2 * PADDING_PX)
        if len(preview_images) == 2:
            single_width = (usable_width - BACK_COVER_PREVIEW_GAP_PX) // 2
        else:
            single_width = usable_width // 2  # center single image

        # Resize and place each preview
        y = BACK_COVER_PREVIEW_TOP_PX
        max_actual_height = 0

        for i, img in enumerate(preview_images):
            fitted = self._fit_dimensions(img, single_width, max_preview_height)
            fitted = self._round_corners(fitted, BACK_COVER_PREVIEW_BORDER_RADIUS_PX)
            fitted = self._add_border(fitted, BACK_COVER_PREVIEW_BORDER_PX, (0, 0, 0, 255))

            if len(preview_images) == 2:
                if i == 0:
                    x = PADDING_PX + (single_width - fitted.width) // 2
                else:
                    x = PADDING_PX + single_width + BACK_COVER_PREVIEW_GAP_PX + (single_width - fitted.width) // 2
            else:
                x = (cover_width - fitted.width) // 2

            base.paste(fitted, (x, y), fitted)
            max_actual_height = max(max_actual_height, fitted.height)
            logger.info(f"Preview {i} placed at ({x}, {y}), size={fitted.size}")

        return y + max_actual_height

    def _draw_barcode(
        self,
        base: Image.Image,
        isbn: str,
        cover_width: int,
        cover_height: int,
    ) -> None:
        """Draw EAN-13 barcode at bottom-right of back cover.

        Position matches KDP barcode space specs: 2.0" x 1.2" with 0.25" margin.

        Args:
            base: Base image to draw on (modified in place)
            isbn: ISBN-13 string (validated, digits only)
            cover_width: Cover width in pixels
            cover_height: Cover height in pixels
        """
        from backoffice.features.ebook.shared.domain.entities.ebook import inches_to_px
        from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.barcode_utils import (
            generate_ean13_barcode,
        )

        rect_w = inches_to_px(BACK_COVER_BARCODE_WIDTH_INCHES, COVER_DPI)
        rect_h = inches_to_px(BACK_COVER_BARCODE_HEIGHT_INCHES, COVER_DPI)
        margin = BACK_COVER_BARCODE_MARGIN_PX

        x = cover_width - rect_w - margin
        y = cover_height - rect_h - margin

        try:
            barcode_img = generate_ean13_barcode(
                isbn=isbn,
                target_width_px=rect_w,
                target_height_px=rect_h,
            )
            # Draw white background first
            draw = ImageDraw.Draw(base)
            draw.rectangle((x, y, x + rect_w, y + rect_h), fill=(255, 255, 255, 255))
            # Paste barcode (convert to RGBA for alpha compositing)
            barcode_rgba = barcode_img.convert("RGBA")
            base.paste(barcode_rgba, (x, y), barcode_rgba)
            logger.info(f"Barcode drawn at ({x}, {y}) for ISBN {isbn}")
        except ValueError as e:
            logger.warning(f"Could not render barcode for ISBN {isbn}: {e}")

    @staticmethod
    def _round_corners(image: Image.Image, radius: int) -> Image.Image:
        """Apply rounded corners to an image using an alpha mask.

        Args:
            image: PIL Image (RGBA)
            radius: Corner radius in pixels

        Returns:
            Image with rounded corners
        """
        mask = Image.new("L", image.size, 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, image.width, image.height), radius=radius, fill=255)
        # Clear corners by drawing full rect then rounded rect
        corner_mask = Image.new("L", image.size, 0)
        corner_draw = ImageDraw.Draw(corner_mask)
        corner_draw.rounded_rectangle(
            (0, 0, image.width, image.height),
            radius=radius,
            fill=255,
        )
        result = image.copy()
        result.putalpha(corner_mask)
        return result

    @staticmethod
    def _add_border(image: Image.Image, border_px: int, color: tuple[int, int, int, int]) -> Image.Image:
        """Add a border around an image.

        Args:
            image: PIL Image (RGBA)
            border_px: Border thickness in pixels
            color: Border color as RGBA tuple

        Returns:
            New image with border added
        """
        bordered = Image.new(
            "RGBA",
            (image.width + 2 * border_px, image.height + 2 * border_px),
            color,
        )
        bordered.paste(image, (border_px, border_px), image)
        return bordered

    @staticmethod
    def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
        """Load a font from the branding fonts directory.

        Args:
            filename: Font filename (e.g. 'Poppins-Bold.ttf')
            size: Font size in pixels

        Returns:
            Loaded font, or default font if not found
        """
        font_path = Path(BACK_COVER_FONT_DIR) / filename
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)
        logger.warning(f"Font not found: {font_path}, using default")
        return cast(ImageFont.FreeTypeFont, ImageFont.load_default())

    @staticmethod
    def _get_font_line_height(font: ImageFont.FreeTypeFont) -> int:
        """Get the line height for a font.

        Args:
            font: PIL font

        Returns:
            Line height in pixels
        """
        bbox = font.getbbox("Ay")
        return int(bbox[3] - bbox[1])

    def _measure_text_block_height(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> int:
        """Measure the total height of a wrapped text block.

        Args:
            text: Text to measure
            font: Font to use
            max_width: Maximum width in pixels

        Returns:
            Total height in pixels
        """
        lines = self._wrap_text(text, font, max_width)
        line_height = self._get_font_line_height(font)
        return len(lines) * (line_height + BACK_COVER_TEXT_LINE_SPACING)

    def _draw_text_centered(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        y: int,
        font: ImageFont.FreeTypeFont,
        fill: tuple[int, int, int] | tuple[int, int, int, int],
        max_width: int,
        cover_width: int,
    ) -> int:
        """Draw centered text, wrapping if needed.

        Args:
            draw: ImageDraw instance
            text: Text to draw
            y: Starting Y position
            font: Font to use
            fill: Text color (RGB or RGBA)
            max_width: Maximum text width in pixels
            cover_width: Total cover width for centering

        Returns:
            Y position after the last line
        """
        lines = self._wrap_text(text, font, max_width)
        line_height = self._get_font_line_height(font)

        for line in lines:
            bbox = font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            x = (cover_width - text_width) // 2
            draw.text((x, y), line, font=font, fill=fill)
            y += line_height + BACK_COVER_TEXT_LINE_SPACING

        return y

    def _draw_text_left(
            self,
            draw: ImageDraw.ImageDraw,
            text: str,
            y: int,
            font: ImageFont.FreeTypeFont,
            fill: tuple[int, int, int] | tuple[int, int, int, int],
            max_width: int,
            cover_width: int,
    ) -> int:
        """Draw left aligned text, wrapping if needed.

        Args:
            draw: ImageDraw instance
            text: Text to draw
            y: Starting Y position
            font: Font to use
            fill: Text color (RGB or RGBA)
            max_width: Maximum text width in pixels
            cover_width: Total cover width for centering

        Returns:
            Y position after the last line
        """
        lines = self._wrap_text(text, font, max_width)
        line_height = self._get_font_line_height(font)

        for line in lines:
            bbox = font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            # x = (cover_width - text_width) // 2
            x = PADDING_PX
            draw.text((x, y), line, font=font, fill=fill)
            y += line_height + BACK_COVER_TEXT_LINE_SPACING

        return y

    @staticmethod
    def _wrap_text(
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list[str]:
        """Wrap text to fit within max_width using the given font.

        Args:
            text: Text to wrap
            font: Font for measuring
            max_width: Maximum width in pixels

        Returns:
            List of wrapped lines
        """
        # Estimate chars per line based on average char width
        avg_char_width = int(font.getbbox("x")[2])
        chars_per_line = max(1, max_width // max(1, avg_char_width))
        wrapped = textwrap.wrap(text, width=chars_per_line)

        # Refine: if any line is still too wide, re-wrap tighter
        result: list[str] = []
        for line in wrapped:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            if line_width <= max_width:
                result.append(line)
            else:
                # Split further
                words = line.split()
                current = ""
                for word in words:
                    test = f"{current} {word}".strip()
                    if font.getbbox(test)[2] - font.getbbox(test)[0] <= max_width:
                        current = test
                    else:
                        if current:
                            result.append(current)
                        current = word
                if current:
                    result.append(current)

        return result if result else [text]
