"""KDP assembly provider for Amazon KDP paperback PDF generation."""

import logging
from io import BytesIO
from typing import cast

import img2pdf  # type: ignore[import-not-found]
from PIL import Image

from backoffice.domain.entities.ebook import (
    Ebook,
    KDPExportConfig,
    calculate_spine_width,
    inches_to_px,
)
from backoffice.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.infrastructure.utils.color_utils import ensure_cmyk
from backoffice.infrastructure.utils.spine_generator import generate_spine

logger = logging.getLogger(__name__)


class KDPAssemblyProvider:
    """Assembly provider for Amazon KDP paperback format.

    Generates single PDF with:
    - Back cover (left)
    - Spine (center)
    - Front cover (right)
    - Proper bleed (0.125" on all outer edges)
    - CMYK color mode
    - 300 DPI resolution
    """

    async def assemble_kdp_paperback(
        self,
        ebook: Ebook,
        back_cover_bytes: bytes,
        front_cover_bytes: bytes,
        kdp_config: KDPExportConfig,
    ) -> bytes:
        """Assemble KDP-ready PDF with back, spine, and front.

        Args:
            ebook: Ebook entity with metadata
            back_cover_bytes: Back cover image bytes (CMYK TIFF)
            front_cover_bytes: Front cover image bytes (will be converted to CMYK)
            kdp_config: KDP export configuration

        Returns:
            PDF bytes ready for KDP upload

        Raises:
            DomainError: If assembly fails or requirements not met
        """
        # 1. Calculate dimensions (rounded to even)
        trim_width_px = inches_to_px(kdp_config.trim_size[0])
        trim_height_px = inches_to_px(kdp_config.trim_size[1])
        bleed_px = inches_to_px(kdp_config.bleed_size)

        # Validate page_count is present
        if ebook.page_count is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook must have page_count for KDP assembly",
                actionable_hint="Regenerate the ebook to populate page_count",
            )

        spine_width_inches = calculate_spine_width(ebook.page_count, kdp_config.paper_type)
        spine_width_px = inches_to_px(spine_width_inches)

        # ✅ Spine height includes bleed top/bottom
        spine_height_px = trim_height_px + 2 * bleed_px

        logger.info(
            f"KDP dimensions: trim={trim_width_px}x{trim_height_px}px, "
            f"bleed={bleed_px}px, spine={spine_width_px}px"
        )

        # 2. Generate spine
        spine_bytes = generate_spine(
            front_cover_bytes=front_cover_bytes,
            spine_width_px=spine_width_px,
            spine_height_px=spine_height_px,
            page_count=ebook.page_count,
            paper_type=kdp_config.paper_type,
            title=ebook.title,
            author=ebook.author,
            icc_cmyk_profile=kdp_config.icc_cmyk_profile,
        )

        # 3. Load and normalize all to CMYK
        back_img = ensure_cmyk(Image.open(BytesIO(back_cover_bytes)), kdp_config.icc_cmyk_profile)
        spine_img = ensure_cmyk(Image.open(BytesIO(spine_bytes)), kdp_config.icc_cmyk_profile)
        front_img = ensure_cmyk(Image.open(BytesIO(front_cover_bytes)), kdp_config.icc_cmyk_profile)

        # 4. ✅ Validate dimensions
        expected_back = (trim_width_px + bleed_px, trim_height_px + 2 * bleed_px)
        expected_spine = (spine_width_px, trim_height_px + 2 * bleed_px)
        expected_front = (trim_width_px + bleed_px, trim_height_px + 2 * bleed_px)

        if back_img.size != expected_back:
            # Back may need resizing (same as front cover)
            logger.warning(
                f"Back cover size mismatch: {back_img.size} != {expected_back}, resizing..."
            )
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
            logger.warning(
                f"Front cover size mismatch: {front_img.size} != {expected_front}, resizing..."
            )
            front_img = front_img.resize(expected_front, Image.Resampling.LANCZOS)

        # 5. Assemble horizontally
        total_width = bleed_px + trim_width_px + spine_width_px + trim_width_px + bleed_px
        total_height = trim_height_px + 2 * bleed_px

        logger.info(f"Full cover dimensions: {total_width}x{total_height}px")

        full_cover = Image.new("CMYK", (total_width, total_height), (0, 0, 0, 0))

        # Paste back (position 0)
        full_cover.paste(back_img, (0, 0))

        # Paste spine
        full_cover.paste(spine_img, (bleed_px + trim_width_px, 0))

        # Paste front
        full_cover.paste(front_img, (bleed_px + trim_width_px + spine_width_px, 0))

        # 6. Save as TIFF with DPI
        cover_buffer = BytesIO()
        full_cover.save(
            cover_buffer, format="TIFF", compression="tiff_adobe_deflate", dpi=(300, 300)
        )
        cover_tiff_bytes = cover_buffer.getvalue()

        # 7. ✅ Convert to PDF with img2pdf (preserves CMYK)
        layout = img2pdf.get_fixed_dpi_layout_fun((300, 300))
        pdf_bytes = cast(bytes, img2pdf.convert([cover_tiff_bytes], layout_fun=layout))

        # 8. Validate KDP requirements
        self._validate_kdp_requirements(ebook.page_count, kdp_config)

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
                message=(
                    f"KDP {config.paper_type} requires {min_required}-{max_required} pages, "
                    f"got {page_count}"
                ),
                actionable_hint="Adjust page count or use different paper type",
            )

        logger.info(f"✅ KDP validation passed: {page_count} pages ({config.paper_type})")
