"""Use case for regenerating a single content/coloring page."""

import base64
import logging

from backoffice.features.ebook.regeneration.domain.events.content_page_regenerated_event import (
    ContentPageRegeneratedEvent,
)
from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.services.page_generation import (
    ContentPageGenerationService,
)
from backoffice.features.ebook.shared.domain.services.prompt_template_engine import (
    PromptTemplateEngine,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class RegenerateContentPageUseCase:
    """Regenerate a single content/coloring page of an ebook.

    This regenerates ONLY one specific content page while keeping:
    - Front cover
    - Back cover
    - All other content pages
    - Same theme and metadata
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        page_service: ContentPageGenerationService,
        regeneration_service: RegenerationService,
        event_bus: EventBus,
    ):
        """Initialize regenerate content page use case.

        Args:
            ebook_repository: Repository for ebook persistence
            page_service: Service for page generation
            regeneration_service: Service for regeneration operations
            event_bus: Event bus for domain events
        """
        self.ebook_repository = ebook_repository
        self.page_service = page_service
        self.regeneration_service = regeneration_service
        self.event_bus = event_bus

    async def execute(
        self,
        ebook_id: int,
        page_index: int,
        prompt_override: str | None = None,
    ) -> Ebook:
        """Regenerate a specific content page of an ebook.

        Args:
            ebook_id: ID of the ebook
            page_index: Index of the page to regenerate (1-based, excluding cover)
            prompt_override: Optional custom prompt for page generation

        Returns:
            Updated ebook with regenerated page

        Raises:
            ValueError: If ebook not found, not in DRAFT status, or invalid page index
        """
        # Retrieve the ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise ValueError(f"Ebook with id {ebook_id} not found")

        # Business rule: only DRAFT ebooks can be modified
        if ebook.status != EbookStatus.DRAFT:
            raise ValueError(f"Cannot regenerate page for ebook with status {ebook.status.value}. " f"Only DRAFT ebooks can be modified.")

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise ValueError("Cannot regenerate page: ebook structure is missing. " "Please regenerate the entire ebook instead.")

        pages_meta = ebook.structure_json["pages_meta"]

        # Validate page index (must be between cover and back cover)
        if page_index < 1 or page_index >= len(pages_meta) - 1:
            raise ValueError(f"Invalid page index {page_index}. " f"Must be between 1 and {len(pages_meta) - 2} (content pages only).")

        logger.info(f"🔄 Regenerating CONTENT PAGE {page_index} for ebook {ebook_id}: {ebook.title}")

        # Step 1: Generate new page with B&W coloring style
        page_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.BLACK_WHITE,
        )

        # Use theme from ebook if available
        prompt = prompt_override or f"{ebook.theme_id} themed coloring page"

        new_page_data = await self.page_service.generate_single_page(
            prompt=prompt,
            spec=page_spec,
            seed=None,  # Random seed for variety
        )

        logger.info(f"✅ Page regenerated: {len(new_page_data)} bytes")

        # Step 2: Rebuild PDF with new page using RegenerationService
        # Build list of all pages with the new page replacing the old one
        assembled_pages = []
        for i, page_meta in enumerate(pages_meta):
            if i == page_index:
                # Use new generated page
                page_data = new_page_data
                logger.info(f"📝 Replacing page {page_index} with newly generated content")
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
            filename_suffix=f"page{page_index}_regenerated",
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

        # Step 4: Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)
        logger.info(f"✅ Ebook {ebook_id} updated with regenerated page {page_index}")

        # Step 5: Emit domain event
        await self.event_bus.publish(
            ContentPageRegeneratedEvent(
                ebook_id=ebook_id,
                title=updated_ebook.title or "Untitled",
                page_index=page_index,
                prompt_used=prompt,
                custom_prompt=prompt_override is not None,
            )
        )

        return updated_ebook
