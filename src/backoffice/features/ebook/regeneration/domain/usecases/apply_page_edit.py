"""Use case for applying a page edit (saving preview image to DB and rebuilding PDF)."""

import base64
import logging

from backoffice.features.ebook.regeneration.domain.events.content_page_regenerated_event import (
    ContentPageRegeneratedEvent,
)
from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class ApplyPageEditUseCase:
    """Apply a page edit by saving the preview image to DB and rebuilding PDF.

    This use case:
    1. Receives a base64-encoded image (from preview modal)
    2. Updates the ebook's structure_json with the new image
    3. Rebuilds the PDF with the new page
    4. Resets APPROVED ebook to DRAFT if necessary
    5. Saves to DB and storage
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        regeneration_service: RegenerationService,
        event_bus: EventBus,
    ):
        """Initialize apply page edit use case.

        Args:
            ebook_repository: Repository for ebook persistence
            regeneration_service: Service for PDF reassembly and upload
            event_bus: Event bus for domain events
        """
        self.ebook_repository = ebook_repository
        self.regeneration_service = regeneration_service
        self.event_bus = event_bus

    async def execute(
        self,
        ebook_id: int,
        page_index: int,
        image_base64: str,
    ) -> Ebook:
        """Apply the page edit by saving the image and rebuilding PDF.

        Args:
            ebook_id: ID of the ebook
            page_index: Index of the page to update (1-based, content pages only)
            image_base64: Base64-encoded image data from preview

        Returns:
            Updated ebook with new page and PDF

        Raises:
            DomainError: If ebook not found, invalid status, or invalid data
        """
        # Retrieve the ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise DomainError(
                code=ErrorCode.EBOOK_NOT_FOUND,
                message=f"Ebook with id {ebook_id} not found",
                actionable_hint="Verify the ebook ID exists",
            )

        # Business rule: only DRAFT ebooks can be modified
        if ebook.status != EbookStatus.DRAFT:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Cannot apply edit for ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT ebooks can be modified",
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Cannot apply edit: ebook structure is missing",
                actionable_hint="Please regenerate the entire ebook first",
            )

        pages_meta = ebook.structure_json["pages_meta"]

        # Validate page index
        if page_index < 1 or page_index >= len(pages_meta) - 1:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid page index {page_index}",
                actionable_hint=f"Must be between 1 and {len(pages_meta) - 2} (content pages only)",
            )

        logger.info(f"💾 Applying edit for page {page_index} of ebook {ebook_id}: {ebook.title}")

        # Step 1: Decode image from base64
        try:
            new_page_data = base64.b64decode(image_base64)
        except Exception as e:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid base64 image data",
                actionable_hint="Ensure the image data is properly encoded",
            ) from e

        logger.info(f"✅ Decoded new page image: {len(new_page_data)} bytes")

        # Step 2: Rebuild PDF with new page using RegenerationService
        # Build list of all pages with the new page replacing the old one
        assembled_pages = []
        for i, page_meta in enumerate(pages_meta):
            if i == page_index:
                # Use new edited page
                page_data = new_page_data
                logger.info(f"📝 Replacing page {page_index} with edited version")
            else:
                # Keep existing page
                page_data = base64.b64decode(page_meta["image_data_base64"])

            assembled_pages.append(
                AssembledPage(
                    page_number=page_meta["page_number"],
                    title=page_meta.get("title", f"Page {page_meta['page_number']}"),
                    image_data=page_data,
                    image_format=page_meta.get("image_format", "PNG"),
                )
            )

        # Use RegenerationService to assemble PDF, save to DB, and upload to storage
        pdf_path, preview_url = await self.regeneration_service.rebuild_and_upload_pdf(
            ebook=ebook,
            assembled_pages=assembled_pages,
            ebook_repository=self.ebook_repository,
            filename_suffix=f"page{page_index}_edited",
        )

        # Update ebook with new preview URL
        ebook.preview_url = preview_url

        # Step 3: Update structure_json with new page
        updated_pages_meta = pages_meta.copy()
        updated_pages_meta[page_index] = {
            "page_number": page_index,
            "title": f"Page {page_index}",
            "image_format": "PNG",
            "image_data_base64": base64.b64encode(new_page_data).decode(),
        }

        ebook.structure_json = {"pages_meta": updated_pages_meta}

        # Step 4: Reset APPROVED to DRAFT if necessary
        if ebook.status == EbookStatus.APPROVED:
            logger.info(f"⚠️ Resetting ebook {ebook_id} from APPROVED to DRAFT due to page edit")
            ebook.status = EbookStatus.DRAFT

        # Step 5: Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)
        logger.info(f"✅ Ebook {ebook_id} saved with edited page {page_index}")

        # Step 6: Emit domain event
        await self.event_bus.publish(
            ContentPageRegeneratedEvent(
                ebook_id=ebook_id,
                title=updated_ebook.title or "Untitled",
                page_index=page_index,
                prompt_used="[Edited via modal]",
            )
        )

        return updated_ebook
