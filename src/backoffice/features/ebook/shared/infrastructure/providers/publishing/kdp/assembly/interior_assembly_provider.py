"""KDP interior assembly provider for Amazon KDP manuscript/interior PDF generation."""

import base64
import logging
from io import BytesIO

import img2pdf
from PIL import Image

from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    KDPExportConfig,
    inches_to_px,
)
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode

logger = logging.getLogger(__name__)


class KDPInteriorAssemblyProvider:
    """Assembly provider for Amazon KDP interior/manuscript format.

    Generates PDF with:
    - Content pages only (excludes cover and back cover)
    - Proper bleed (0.125" on all edges)
    - Black & white or color mode (based on page metadata)
    - 300 DPI resolution
    - KDP-compliant dimensions (8×10" default)
    """

    async def assemble_kdp_interior(
        self,
        ebook: Ebook,
        kdp_config: KDPExportConfig,
    ) -> bytes:
        """Assemble KDP-ready interior/manuscript PDF.

        Args:
            ebook: Ebook entity with structure_json containing pages
            kdp_config: KDP export configuration

        Returns:
            PDF bytes ready for KDP interior upload

        Raises:
            DomainError: If assembly fails or requirements not met
        """
        # 1. Validate ebook structure
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook structure missing pages metadata",
                actionable_hint="Regenerate the ebook",
            )

        pages_meta = ebook.structure_json["pages_meta"]
        if len(pages_meta) < 3:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook must have at least 3 pages (cover + content + back)",
                actionable_hint="Regenerate the ebook",
            )

        # 2. Calculate dimensions
        trim_width_px = inches_to_px(kdp_config.trim_size[0])
        trim_height_px = inches_to_px(kdp_config.trim_size[1])
        bleed_px = inches_to_px(kdp_config.bleed_size)

        # Interior pages have bleed on all 4 sides
        page_width_px = trim_width_px + 2 * bleed_px
        page_height_px = trim_height_px + 2 * bleed_px

        logger.info(
            f"KDP interior dimensions: trim={trim_width_px}x{trim_height_px}px, "
            f"with bleed={page_width_px}x{page_height_px}px"
        )

        # 3. Extract interior pages (exclude first and last - cover and back cover)
        interior_pages = pages_meta[1:-1]
        logger.info(f"Processing {len(interior_pages)} interior pages (excluding cover and back)")

        if not interior_pages:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="No interior pages found (only cover and back cover)",
                actionable_hint="Ebook must have content pages between cover and back",
            )

        # 3b. Auto-complete to KDP minimum (24 pages) if needed
        min_pages_required = 24  # KDP minimum for standard_color
        if len(interior_pages) < min_pages_required:
            pages_to_add = min_pages_required - len(interior_pages)
            logger.info(
                f"⚠️ Interior has {len(interior_pages)} pages (< {min_pages_required}), "
                f"adding {pages_to_add} blank page(s) for KDP compliance"
            )

            # Generate blank white page (2626x2626 for 8.5" + bleed @ 300 DPI)
            blank_img = Image.new("RGB", (2626, 2626), (255, 255, 255))
            buffer = BytesIO()
            blank_img.save(buffer, format="PNG")
            blank_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Add blank pages before the validation
            for i in range(pages_to_add):
                interior_pages.append(
                    {
                        "page_number": len(interior_pages) + 1,
                        "title": f"Blank Page {i + 1}",
                        "image_data_base64": blank_base64,
                        "format": "PNG",
                        "color_mode": "BLACK_WHITE",
                    }
                )

            logger.info(
                f"✅ Added {pages_to_add} blank page(s), new total: {len(interior_pages)} interior pages"
            )

        # 4. Process each interior page
        processed_images = []
        for idx, page_meta in enumerate(interior_pages, start=1):
            page_number = page_meta.get("page_number", idx)
            logger.info(
                f"Processing interior page {idx}/{len(interior_pages)} (page_number={page_number})"
            )

            # Decode base64 image
            image_data = base64.b64decode(page_meta["image_data_base64"])
            img = Image.open(BytesIO(image_data))

            # Resize to exact dimensions with bleed
            if img.size != (page_width_px, page_height_px):
                logger.warning(
                    f"Page {page_number} size mismatch: {img.size} != {page_width_px}x{page_height_px}, resizing..."
                )
                img = img.resize((page_width_px, page_height_px), Image.Resampling.LANCZOS)

            # Ensure RGB mode (KDP interior can be RGB or CMYK, but RGB is simpler)
            if img.mode != "RGB":
                logger.info(f"Converting page {page_number} from {img.mode} to RGB")
                img = img.convert("RGB")

            # Save to bytes with 300 DPI
            img_buffer = BytesIO()
            img.save(img_buffer, format="PNG", dpi=(300, 300))
            processed_images.append(img_buffer.getvalue())

        # 5. Convert to PDF with img2pdf
        logger.info(f"Converting {len(processed_images)} pages to PDF...")
        layout = img2pdf.get_fixed_dpi_layout_fun((300, 300))
        pdf_bytes = bytes(img2pdf.convert(processed_images, layout_fun=layout))

        # 6. Validate KDP requirements
        self._validate_kdp_interior_requirements(len(interior_pages), kdp_config)

        logger.info(
            f"✅ KDP interior PDF assembled: {len(pdf_bytes)} bytes ({len(interior_pages)} pages)"
        )
        return pdf_bytes

    def _validate_kdp_interior_requirements(self, page_count: int, config: KDPExportConfig):
        """Validate KDP interior requirements.

        Args:
            page_count: Number of interior pages
            config: KDP configuration

        Raises:
            DomainError: If requirements not met
        """
        # KDP requires minimum pages (varies by paper type)
        min_pages = {"premium_color": 24, "standard_color": 24, "white": 24, "cream": 24}
        max_pages = {"premium_color": 828, "standard_color": 828, "white": 828, "cream": 828}

        min_required = min_pages.get(config.paper_type, 24)
        max_required = max_pages.get(config.paper_type, 828)

        if page_count < min_required or page_count > max_required:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(
                    f"KDP {config.paper_type} interior requires {min_required}-{max_required} pages, "
                    f"got {page_count}"
                ),
                actionable_hint="Adjust page count or use different paper type",
            )

        logger.info(f"✅ KDP interior validation passed: {page_count} pages ({config.paper_type})")
