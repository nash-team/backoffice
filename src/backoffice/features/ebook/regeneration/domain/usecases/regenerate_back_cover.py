"""Use case for regenerating ebook back cover only."""

import base64
import logging

from backoffice.features.ebook.regeneration.domain.events.back_cover_regenerated_event import (
    BackCoverRegeneratedEvent,
)
from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.services.cover_generation import CoverGenerationService
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class RegenerateBackCoverUseCase:
    """Regenerate the back cover of a coloring book ebook.

    This regenerates ONLY the back cover while keeping:
    - Front cover (extracts color from it)
    - All content pages
    - Same theme and metadata
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        cover_service: CoverGenerationService,
        regeneration_service: RegenerationService,
        event_bus: EventBus,
    ):
        """Initialize regenerate back cover use case.

        Args:
            ebook_repository: Repository for ebook persistence
            cover_service: Service for cover generation
            regeneration_service: Service for regeneration operations
            event_bus: Event bus for domain events
        """
        self.ebook_repository = ebook_repository
        self.cover_service = cover_service
        self.regeneration_service = regeneration_service
        self.event_bus = event_bus

    async def execute(
        self,
        ebook_id: int,
    ) -> Ebook:
        """Regenerate the back cover of an ebook.

        Args:
            ebook_id: ID of the ebook

        Returns:
            Updated ebook with new back cover

        Raises:
            ValueError: If ebook not found or not in PENDING status
        """
        # Retrieve the ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise ValueError(f"Ebook with id {ebook_id} not found")

        # Business rule: only DRAFT ebooks can be modified
        if ebook.status != EbookStatus.DRAFT:
            raise ValueError(f"Cannot regenerate back cover for ebook with status {ebook.status.value}. " f"Only DRAFT ebooks can be modified.")

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise ValueError("Cannot regenerate back cover: ebook structure is missing. " "Please regenerate the entire ebook instead.")

        pages_meta = ebook.structure_json["pages_meta"]
        if len(pages_meta) < 2:
            raise ValueError("Cannot regenerate back cover: ebook must have at least 2 pages (cover + back)")

        logger.info(f"🔄 Regenerating BACK COVER for ebook {ebook_id}: {ebook.title}")

        # Step 1: Extract front cover bytes (first page)
        front_cover_meta = pages_meta[0]
        front_cover_bytes = base64.b64decode(front_cover_meta["image_data_base64"])

        # Step 2: Remove text from cover using injected provider
        logger.info("🔄 Creating back cover (same image without text)...")

        # Load KDP config for barcode dimensions
        from backoffice.features.ebook.shared.domain.entities.ebook import KDPExportConfig

        kdp_config = KDPExportConfig()

        back_cover_data = await self.cover_service.cover_port.remove_text_from_cover(
            image_bytes=front_cover_bytes,
            barcode_width_inches=kdp_config.barcode_width,
            barcode_height_inches=kdp_config.barcode_height,
            barcode_margin_inches=kdp_config.barcode_margin,
        )

        logger.info(f"✅ Back cover regenerated: {len(back_cover_data)} bytes")

        # Step 4: Rebuild PDF with new back cover using RegenerationService
        assembled_pages = []

        # Add all pages EXCEPT the last one (old back cover)
        for _i, page_meta in enumerate(pages_meta[:-1]):
            page_data = base64.b64decode(page_meta["image_data_base64"])
            assembled_pages.append(
                AssembledPage(
                    page_number=page_meta["page_number"],
                    title=page_meta.get("title", f"Page {page_meta['page_number']}"),
                    image_data=page_data,
                    image_format=page_meta.get("image_format", "PNG"),
                )
            )

        # Add new back cover as last page
        assembled_pages.append(
            AssembledPage(
                page_number=len(pages_meta),
                title="Back Cover",
                image_data=back_cover_data,
                image_format="PNG",
            )
        )

        # Use RegenerationService to assemble PDF, save to DB, and upload to storage
        pdf_path, preview_url = await self.regeneration_service.rebuild_and_upload_pdf(
            ebook=ebook,
            assembled_pages=assembled_pages,
            ebook_repository=self.ebook_repository,
            filename_suffix="back_cover_regenerated",
        )

        # Update ebook with new preview URL
        ebook.preview_url = preview_url

        # Step 5: Update structure_json with new back cover
        # Replace last page (old back cover) with new back cover
        updated_pages_meta = pages_meta[:-1]  # Keep all except last
        updated_pages_meta.append(
            {
                "page_number": len(pages_meta),
                "title": "Back Cover",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(back_cover_data).decode(),
            }
        )

        ebook.structure_json = {"pages_meta": updated_pages_meta}

        # Step 6: Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)
        logger.info(f"✅ Ebook {ebook_id} updated with new back cover")

        # Step 7: Emit domain event
        await self.event_bus.publish(
            BackCoverRegeneratedEvent(
                ebook_id=ebook_id,
                title=updated_ebook.title or "Untitled",
            )
        )

        return updated_ebook
