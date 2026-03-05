"""KDP assembly provider for Amazon KDP paperback PDF generation."""

import logging
from io import BytesIO
from typing import cast

import img2pdf
from PIL import Image

from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    KDPExportConfig,
    calculate_spine_width,
    inches_to_px,
)
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils import (
    color_utils,
    spine_generator,
)

logger = logging.getLogger(__name__)


class KDPAssemblyProvider:
    """Assembly provider for Amazon KDP paperback format.

    Generates single PDF with:
    - Back cover (left)
    - Spine (center)
    - Front cover (right)
    - Proper bleed (0.125" on all outer edges)
    - RGB color mode (KDP requirement - will convert to CMYK for print)
    - 300 DPI resolution
    """

    async def assemble_kdp_paperback(
        self,
        ebook: Ebook,
        back_cover_bytes: bytes,
        front_cover_bytes: bytes,
        kdp_config: KDPExportConfig,
        isbn: str | None = None,
        spine_colors: list = None

    ) -> bytes:
        """Assemble KDP-ready PDF with back, spine, and front.

        Args:
            ebook: Ebook entity with metadata
            back_cover_bytes: Back cover image bytes (RGB PNG/JPEG)
            front_cover_bytes: Front cover image bytes (RGB PNG/JPEG)
            kdp_config: KDP export configuration
            isbn: ISBN that should be used
            spine_colors: Colors that should be used for spine (background and text)

        Returns:
            PDF bytes ready for KDP upload (RGB mode - KDP will convert to CMYK)

        Raises:
            DomainError: If assembly fails or requirements not met
        """
        # 1. Calculate dimensions (rounded to even) https://kdp.amazon.com/cover-calculator
        front_cover_width_px = inches_to_px(kdp_config.trim_size[0])
        front_cover_height_px = inches_to_px(kdp_config.trim_size[1])

        bleed_px = inches_to_px(kdp_config.bleed_size)

        # Validate page_count is present
        if ebook.page_count is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook must have page_count for KDP assembly",
                actionable_hint="Regenerate the ebook to populate page_count",
            )

        spine_width_inches, spine_safe_area_inches = calculate_spine_width(ebook.page_count + 1, # legal page to consider
                                                        kdp_config.paper_type,
                                                        kdp_config.gutter_margin_size)

        spine_dimensions_inches = (spine_width_inches,
                                   kdp_config.trim_size[1] + kdp_config.top_margin_size + kdp_config.bottom_margin_size)
        spine_dimensions_px = (inches_to_px(spine_dimensions_inches[0]), inches_to_px(spine_dimensions_inches[1]))
        spine_safe_area_dimensions_inches = (spine_safe_area_inches,
                                             kdp_config.trim_size[1]-2*kdp_config.bleed_size - kdp_config.top_margin_size + kdp_config.bottom_margin_size)
        spine_safe_area_dimensions_px = (inches_to_px(spine_safe_area_dimensions_inches[0]), inches_to_px(spine_safe_area_dimensions_inches[1]))

        logger.info(f"KDP Spine dimensions: {spine_dimensions_inches[0]:.6f}x{spine_dimensions_inches[1]:.6f} inches => {spine_dimensions_px[0]}x{spine_dimensions_px[1]}px, bleed={kdp_config.bleed_size} inches => {bleed_px}px")
        logger.info(f"KDP Spine safe area: {spine_safe_area_dimensions_inches[0]:.6f}x{spine_safe_area_dimensions_inches[1]:.6f} inches ({spine_safe_area_dimensions_px[0]}x{spine_safe_area_dimensions_px[1]}px)")

        logger.info(f"KDP front cover dimensions: trim={kdp_config.trim_size[0]:.6f}x{kdp_config.trim_size[1]:.6f} ({front_cover_width_px}x{front_cover_height_px}px), bleed={bleed_px}px")

        # 2. Generate spine (RGB format - KDP requirement)
        spine_bytes = spine_generator.generate_spine(
            front_cover_bytes=front_cover_bytes,
            spine_width_px=spine_dimensions_px[0],
            spine_height_px=spine_dimensions_px[1],
            spine_colors=spine_colors,
            page_count=ebook.page_count + 1, # legal page to add
            paper_type=kdp_config.paper_type,
            title=ebook.title,
            author=ebook.author,
        )

        # 3. Load and normalize all to RGB (KDP requirement)
        back_img = color_utils.ensure_rgb(Image.open(BytesIO(back_cover_bytes)))
        spine_img = color_utils.ensure_rgb(Image.open(BytesIO(spine_bytes)))
        front_img = color_utils.ensure_rgb(Image.open(BytesIO(front_cover_bytes)))

        # 4. ✅ Validate dimensions (front_cover_width and front_cover_height already include bleed)
        expected_back = (inches_to_px(kdp_config.trim_size[0] + kdp_config.side_margin_size),
                         inches_to_px(kdp_config.trim_size[1] + kdp_config.top_margin_size + kdp_config.bottom_margin_size))

        expected_spine = (spine_dimensions_px[0], spine_dimensions_px[1])

        expected_front = (inches_to_px(kdp_config.trim_size[0] + kdp_config.side_margin_size),
                          inches_to_px(kdp_config.trim_size[1] + kdp_config.top_margin_size + kdp_config.bottom_margin_size))

        if back_img.size != expected_back:
            # Back may need resizing (same as front cover)
            logger.warning(f"Back cover size mismatch: {back_img.size} != {expected_back}, resizing...")
            back_img = back_img.resize(expected_back, Image.Resampling.LANCZOS)

        if spine_img.size != expected_spine:
            logger.error(f"Spine size mismatch: {spine_img.size} != {expected_spine}")
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Spine dimensions incorrect: {spine_img.size} != {expected_spine}",
                actionable_hint="Check spine generation",
            )

        if front_img.size != expected_front:
            # Front may need resizing
            logger.warning(f"Front cover size mismatch: {front_img.size} != {expected_front}, resizing...")
            front_img = front_img.resize(expected_front, Image.Resampling.LANCZOS)

        # 5. Assemble horizontally
        total_width = 2*inches_to_px(kdp_config.trim_size[0]) + spine_dimensions_px[0] + 2*inches_to_px(kdp_config.side_margin_size)
        total_height = inches_to_px(kdp_config.trim_size[1]) + inches_to_px(kdp_config.top_margin_size + kdp_config.bottom_margin_size)

        logger.info(f"Full cover dimensions: {total_width}x{total_height}px")

        # RGB mode with white background (KDP requirement)
        full_cover = Image.new("RGB", (total_width, total_height), (255, 255, 255))

        # Add barcode space to back cover BEFORE pasting
        # (back cover has left bleed + trim, no right bleed - spine comes after)
        logger.info("📦 Adding KDP barcode space to back cover...")
        back_buffer = BytesIO()
        # Use PNG format (RGB mode for KDP)
        back_img.save(back_buffer, format="PNG")

        # Paste back (position 0)
        full_cover.paste(back_img, (0, 0))

        # Paste spine
        full_cover.paste(spine_img, (inches_to_px(kdp_config.trim_size[0]) + inches_to_px(kdp_config.side_margin_size), 0))

        # Paste front
        full_cover.paste(front_img, (inches_to_px(kdp_config.trim_size[0]) + inches_to_px(kdp_config.side_margin_size) + spine_dimensions_px[0], 0))

        # 6. Save as PNG with DPI (RGB mode for KDP)
        cover_buffer = BytesIO()
        full_cover.save(cover_buffer, format="PNG", dpi=(300, 300))

        # save the image of the full cover in temp folder
        full_cover.save("/tmp/full_cover.png", format="PNG", dpi=(300, 300))

        cover_tiff_bytes = cover_buffer.getvalue()

        # 7. ✅ Convert to PDF with img2pdf (preserves RGB - KDP will convert to CMYK for print)
        layout = img2pdf.get_fixed_dpi_layout_fun((300, 300))
        pdf_bytes = cast(bytes, img2pdf.convert([cover_tiff_bytes], layout_fun=layout))

        # 8. Validate KDP requirements
        self._validate_kdp_requirements(ebook.page_count + 1, kdp_config)

        logger.info(f"✅ KDP PDF assembled: {len(pdf_bytes)} bytes")
        return pdf_bytes

    def _validate_kdp_requirements(self, page_count: int, config: KDPExportConfig):
        """Validate KDP requirements.

        Args:
            page_count: Number of pages
            config: KDP configuration

        Raises:
            DomainError: If requirements not met
        """
        # Different paper types have different page count requirements
        min_pages = {"premium_color": 24, "standard_color": 24, "white": 24, "cream": 24}
        max_pages = {"premium_color": 828, "standard_color": 828, "white": 828, "cream": 828}

        min_required = min_pages.get(config.paper_type, 24)
        max_required = max_pages.get(config.paper_type, 828)

        if page_count < min_required or page_count > max_required:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(f"KDP {config.paper_type} requires {min_required}-{max_required} pages, got {page_count}"),
                actionable_hint="Adjust page count or use different paper type",
            )

        logger.info(f"✅ KDP validation passed: {page_count} pages ({config.paper_type})")
