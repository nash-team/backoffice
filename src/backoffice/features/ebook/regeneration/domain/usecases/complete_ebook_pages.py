"""Use case for completing ebook pages to reach KDP minimum (24 pages)."""

import base64
import logging
from io import BytesIO

from PIL import Image

from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort

logger = logging.getLogger(__name__)

KDP_MIN_PAGES = 24  # KDP minimum for standard_color


class CompleteEbookPagesUseCase:
    """Complete ebook with blank pages to reach KDP minimum (24 pages).

    This use case is useful for testing KDP exports without generating full ebooks.
    It adds white blank pages between the last content page and the back cover.
    """

    def __init__(self, ebook_repository: EbookPort, regeneration_service: RegenerationService):
        """Initialize the use case.

        Args:
            ebook_repository: Repository for ebook persistence
            regeneration_service: Service for PDF reassembly after adding pages
        """
        self.ebook_repository = ebook_repository
        self.regeneration_service = regeneration_service

    async def execute(self, ebook_id: int, target_pages: int = KDP_MIN_PAGES) -> Ebook:
        """Complete ebook with blank pages to reach target INTERIOR page count.

        Args:
            ebook_id: ID of the ebook to complete
            target_pages: Target INTERIOR page count (default: 24 for KDP minimum)
                         Total pages will be target_pages + 2 (cover + back cover)

        Returns:
            Updated ebook with blank pages added

        Raises:
            DomainError: If ebook not found or already has enough pages
        """
        # 1. Load ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise DomainError(
                code=ErrorCode.EBOOK_NOT_FOUND,
                message=f"Ebook with ID {ebook_id} not found",
                actionable_hint="Verify ebook ID",
            )

        # 2. Check if ebook has structure
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook has no structure - cannot complete pages",
                actionable_hint="Generate ebook first",
            )

        pages_meta = ebook.structure_json["pages_meta"]
        total_pages = len(pages_meta)

        # KDP requires interior pages (excluding cover and back cover)
        # So we need: cover (1) + interior (target_pages) + back cover (1) = target_pages + 2 total
        interior_pages = total_pages - 2  # Exclude cover and back cover
        target_total_pages = target_pages + 2  # Add cover and back cover

        # 3. Check if already complete
        if interior_pages >= target_pages:
            logger.info(f"Ebook {ebook_id} already has {interior_pages} interior pages " f"(target: {target_pages}, total: {total_pages})")
            return ebook

        # 4. Calculate pages to add (to interior)
        pages_to_add = target_pages - interior_pages
        logger.info(
            f"Completing ebook {ebook_id}: adding {pages_to_add} blank interior pages "
            f"(current interior: {interior_pages}, target interior: {target_pages}, "
            f"total will be: {target_total_pages})"
        )

        # 5. Generate blank page image (white, 2626x2626px @ 300 DPI for 8.5"x8.5" + 0.125" bleed)
        blank_img = Image.new("RGB", (2626, 2626), (255, 255, 255))
        buffer = BytesIO()
        blank_img.save(buffer, format="PNG")
        blank_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # 6. Extract back cover (last page) to re-add after blank pages
        back_cover = pages_meta.pop()  # Remove last page (back cover)

        # 7. Add blank pages before back cover
        last_page_number = pages_meta[-1]["page_number"] if pages_meta else 0

        for i in range(pages_to_add):
            page_number = last_page_number + i + 1
            pages_meta.append(
                {
                    "page_number": page_number,
                    "title": f"Blank Page {i + 1}",
                    "image_data_base64": blank_base64,
                    "format": "PNG",
                    "color_mode": "BLACK_WHITE",
                }
            )
            logger.info(f"  Added blank page {page_number}")

        # 8. Re-add back cover as last page
        back_cover["page_number"] = pages_meta[-1]["page_number"] + 1
        pages_meta.append(back_cover)

        # 9. Update ebook structure and page count
        ebook.structure_json["pages_meta"] = pages_meta
        ebook.page_count = len(pages_meta)

        # 10. Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)

        # 11. Reassemble PDF with all pages (including new blank pages)
        logger.info(f"🔄 Reassembling PDF with {len(pages_meta)} pages...")
        assembled_pages = self._convert_pages_meta_to_assembled_pages(pages_meta)

        await self.regeneration_service.rebuild_and_upload_pdf(
            ebook=updated_ebook,
            assembled_pages=assembled_pages,
            ebook_repository=self.ebook_repository,
            filename_suffix="completed",
        )

        logger.info(f"✅ Ebook {ebook_id} completed: added {pages_to_add} blank pages " f"(new total: {updated_ebook.page_count}), PDF reassembled")

        return updated_ebook

    def _convert_pages_meta_to_assembled_pages(self, pages_meta: list[dict]) -> list[AssembledPage]:
        """Convert pages_meta from structure_json to AssembledPage objects.

        Args:
            pages_meta: List of page metadata from structure_json

        Returns:
            List of AssembledPage objects ready for PDF assembly
        """
        assembled_pages = []
        for page_data in pages_meta:
            # Decode base64 image data
            image_bytes = base64.b64decode(page_data["image_data_base64"])

            # Create AssembledPage
            assembled_page = AssembledPage(
                page_number=page_data["page_number"],
                title=page_data["title"],
                image_data=image_bytes,
                image_format=page_data.get("image_format", "PNG"),
            )
            assembled_pages.append(assembled_page)

        return assembled_pages
