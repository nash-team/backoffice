"""Use case for regenerating ebook back cover only."""

import base64
import logging
from pathlib import Path

from backoffice.features.ebook_regeneration.domain.events.back_cover_regenerated_event import (
    BackCoverRegeneratedEvent,
)
from backoffice.features.shared.domain.cover_generation import CoverGenerationService
from backoffice.features.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.shared.domain.pdf_assembly import PDFAssemblyService
from backoffice.features.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.shared.domain.ports.ebook.ebook_port import EbookPort
from backoffice.features.shared.domain.ports.file_storage_port import FileStoragePort
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
        assembly_service: PDFAssemblyService,
        file_storage: FileStoragePort,
        event_bus: EventBus,
    ):
        """Initialize regenerate back cover use case.

        Args:
            ebook_repository: Repository for ebook persistence
            cover_service: Service for cover generation
            assembly_service: Service for PDF assembly
            file_storage: Service for file storage (Google Drive)
            event_bus: Event bus for domain events
        """
        self.ebook_repository = ebook_repository
        self.cover_service = cover_service
        self.assembly_service = assembly_service
        self.file_storage = file_storage
        self.event_bus = event_bus

    async def execute(
        self,
        ebook_id: int,
        prompt_override: str | None = None,
    ) -> Ebook:
        """Regenerate the back cover of an ebook.

        Args:
            ebook_id: ID of the ebook
            prompt_override: Optional custom prompt for back cover generation

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
            raise ValueError(
                f"Cannot regenerate back cover for ebook with status {ebook.status.value}. "
                f"Only DRAFT ebooks can be modified."
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise ValueError(
                "Cannot regenerate back cover: ebook structure is missing. "
                "Please regenerate the entire ebook instead."
            )

        pages_meta = ebook.structure_json["pages_meta"]
        if len(pages_meta) < 2:
            raise ValueError(
                "Cannot regenerate back cover: ebook must have at least 2 pages (cover + back)"
            )

        logger.info(f"🔄 Regenerating BACK COVER for ebook {ebook_id}: {ebook.title}")

        # Step 1: Extract front cover bytes (first page)
        front_cover_meta = pages_meta[0]
        front_cover_bytes = base64.b64decode(front_cover_meta["image_data_base64"])

        # Step 2: Remove text from cover using injected provider
        logger.info("🔄 Creating back cover (same image without text)...")

        back_cover_data = await self.cover_service.cover_port.remove_text_from_cover(
            cover_bytes=front_cover_bytes
        )

        logger.info(f"✅ Back cover regenerated: {len(back_cover_data)} bytes")

        # Step 4: Rebuild PDF with new back cover
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
        back_cover_page = AssembledPage(
            page_number=len(pages_meta),
            title="Back Cover",
            image_data=back_cover_data,
            image_format="PNG",
        )
        assembled_pages.append(back_cover_page)

        # Generate PDF
        import tempfile

        pdf_path = Path(tempfile.gettempdir()) / f"ebook_{ebook_id}_back_regenerated.pdf"

        # Split into cover and content pages for assembly
        cover_page = assembled_pages[0]
        content_pages = assembled_pages[1:]

        await self.assembly_service.assemble_ebook(
            cover=cover_page,
            pages=content_pages,
            output_path=str(pdf_path),
        )

        logger.info(f"📄 PDF regenerated with new back cover: {pdf_path}")

        # Step 5: Upload to Google Drive
        if self.file_storage.is_available():
            try:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                filename = f"{ebook.title or 'coloring_book'}_back_regenerated.pdf"
                upload_result = await self.file_storage.upload_ebook(
                    file_bytes=pdf_bytes,
                    filename=filename,
                    metadata={
                        "title": ebook.title or "Untitled",
                        "author": ebook.author or "Unknown",
                        "ebook_id": str(ebook_id),
                        "back_cover_regenerated": "true",
                    },
                )

                # Update ebook with new Drive info
                ebook.drive_id = upload_result.get("storage_id")
                ebook.preview_url = upload_result.get("storage_url")

                logger.info(f"✅ Uploaded to Drive: {ebook.drive_id}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to upload to Drive: {e}")
                # Continue anyway, update with local file path
                ebook.preview_url = f"file://{pdf_path}"

        else:
            logger.warning("⚠️ Google Drive not available, using local file")
            ebook.preview_url = f"file://{pdf_path}"

        # Step 6: Update structure_json with new back cover
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

        # Step 7: Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)
        logger.info(f"✅ Ebook {ebook_id} updated with new back cover")

        # Step 8: Emit domain event
        await self.event_bus.publish(
            BackCoverRegeneratedEvent(
                ebook_id=ebook_id,
                title=updated_ebook.title or "Untitled",
            )
        )

        return updated_ebook
