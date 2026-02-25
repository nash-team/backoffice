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
from backoffice.features.ebook.shared.domain.services.ebook_validator import EbookValidator
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
        prompt: str | None = None,
    ) -> Ebook:
        """Apply the page edit by saving the image and rebuilding PDF.

        Args:
            ebook_id: ID of the ebook
            page_index: Index of the page to update (0 for cover, 1+ for content pages)
            image_base64: Base64-encoded image data from preview
            prompt: Optional prompt to save with the page (for prompt-based regeneration)

        Returns:
            Updated ebook with new page and PDF

        Raises:
            DomainError: If ebook not found, invalid status, or invalid data
        """
        # Validate ebook (exists + editable status + has structure)
        # Allows DRAFT or APPROVED (will reset to DRAFT after edit)
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        ebook = EbookValidator.validate_for_regeneration(ebook, ebook_id)
        if ebook.structure_json is None:  # pragma: no cover — guaranteed by validator
            raise DomainError(code=ErrorCode.VALIDATION_ERROR, message="Ebook has no structure data", actionable_hint="Regenerate the ebook first")

        pages_meta = ebook.structure_json["pages_meta"]

        # Validate page index (0 = cover, 1 to N-2 = content, N-1 = back cover)
        # We allow 0 for cover and 1 to N-2 for content pages (not back cover)
        is_cover = page_index == 0
        if page_index < 0 or page_index >= len(pages_meta) - 1:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid page index {page_index}",
                actionable_hint=f"Must be between 0 (cover) and {len(pages_meta) - 2} (content pages)",
            )

        page_type = "COVER" if is_cover else f"page {page_index}"
        logger.info(f"💾 Applying edit for {page_type} of ebook {ebook_id}: {ebook.title}")

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
        # Preserve existing fields and update image + prompt
        updated_pages_meta = pages_meta.copy()
        existing_page = pages_meta[page_index]

        # Determine title based on page type
        if is_cover:
            title = "Cover"
        else:
            title = existing_page.get("title", f"Page {page_index}")

        # Build updated page meta, preserving prompt if not provided
        updated_page = {
            "page_number": page_index,
            "title": title,
            "image_format": "PNG",
            "image_data_base64": base64.b64encode(new_page_data).decode(),
            "prompt": prompt if prompt is not None else existing_page.get("prompt", ""),
        }
        updated_pages_meta[page_index] = updated_page

        ebook.structure_json = {"pages_meta": updated_pages_meta}

        # Step 4: Reset APPROVED to DRAFT if necessary
        if ebook.status == EbookStatus.APPROVED:
            logger.info(f"⚠️ Resetting ebook {ebook_id} from APPROVED to DRAFT due to page edit")
            ebook.status = EbookStatus.DRAFT

        # Step 5: Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)
        logger.info(f"✅ Ebook {ebook_id} saved with edited {page_type}")

        # Step 6: Emit domain event
        prompt_info = prompt[:50] + "..." if prompt and len(prompt) > 50 else prompt or "[Edited via modal]"
        await self.event_bus.publish(
            ContentPageRegeneratedEvent(
                ebook_id=ebook_id,
                title=updated_ebook.title or "Untitled",
                page_index=page_index,
                prompt_used=prompt_info,
            )
        )

        return updated_ebook
