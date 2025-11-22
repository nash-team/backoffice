"""Use case for regenerating ebook cover (V1 slim)."""

import logging

from backoffice.features.ebook.regeneration.domain.events.cover_regenerated_event import (
    CoverRegeneratedEvent,
)
from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.services.cover_generation import CoverGenerationService
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class RegenerateCoverUseCase:
    """Regenerate the cover of an ebook (V1 slim).

    V1 approach:
    - Only works for ebooks in PENDING status
    - Uses CoverGenerationService from new architecture
    - Regenerates PDF with new cover
    - Uploads to Google Drive
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        cover_service: CoverGenerationService,
        regeneration_service: RegenerationService,
        event_bus: EventBus,
    ):
        """Initialize regenerate cover use case.

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
        """Regenerate the cover of an ebook.

        Args:
            ebook_id: ID of the ebook

        Returns:
            Updated ebook with new cover

        Raises:
            ValueError: If ebook not found or not in PENDING status
        """
        # Retrieve the ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise ValueError(f"Ebook with id {ebook_id} not found")

        # Business rule: only DRAFT ebooks can have their cover regenerated
        if ebook.status != EbookStatus.DRAFT:
            raise ValueError(f"Cannot regenerate cover for ebook with status {ebook.status.value}. " f"Only DRAFT ebooks can be modified.")

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise ValueError("Cannot regenerate cover: ebook structure is missing. " "Please regenerate the entire ebook instead.")

        logger.info(f"🔄 Regenerating cover for ebook {ebook_id}: {ebook.title}")

        # Step 1: Build cover prompt from YAML theme
        from backoffice.features.ebook.shared.domain.services.workflow_helper import (
            build_cover_prompt_from_yaml,
            load_workflow_params,
        )
        from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
            ThemeRepository,
        )

        theme_repo = ThemeRepository()
        cover_prompt = build_cover_prompt_from_yaml(theme_id=ebook.theme_id or "dinosaurs", themes_directory=theme_repo.themes_directory)
        logger.info(f"Using YAML-based prompt: {cover_prompt[:100]}...")

        # Step 2: Load workflow params from YAML theme
        workflow_params = load_workflow_params(
            theme_id=ebook.theme_id or "dinosaurs",
            image_type="cover",
            themes_directory=theme_repo.themes_directory,
        )

        # Step 3: Generate new cover
        cover_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.COLOR,
        )

        cover_data = await self.cover_service.generate_cover(
            prompt=cover_prompt,
            spec=cover_spec,
            seed=None,  # Random cover each time
            workflow_params=workflow_params,
        )

        logger.info(f"✅ Cover regenerated: {len(cover_data)} bytes")

        # Step 3: Rebuild PDF with new cover using RegenerationService
        # Extract pages metadata from structure_json
        import base64

        pages_meta = ebook.structure_json["pages_meta"]

        # Build assembled pages list with new cover
        assembled_pages = [
            AssembledPage(
                page_number=0,
                title=ebook.title or "Cover",
                image_data=cover_data,
                image_format="PNG",
            )
        ]

        # Add content pages (skip old cover at page_number=0)
        for page_meta in pages_meta:
            if page_meta["page_number"] == 0:
                continue  # Skip the old cover

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
            filename_suffix="cover_regenerated",
        )

        # Update ebook with new preview URL
        ebook.preview_url = preview_url

        # Step 4: Update structure_json with new cover

        # Replace old cover (page_number=0) with new cover in structure_json
        updated_pages_meta = [
            {
                "page_number": 0,
                "title": "Cover",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(cover_data).decode(),
            }
        ]
        # Keep all other pages (skip old cover)
        for page_meta in pages_meta:
            if page_meta["page_number"] != 0:
                updated_pages_meta.append(page_meta)

        ebook.structure_json = {"pages_meta": updated_pages_meta}

        # Step 5: Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)
        logger.info(f"✅ Ebook {ebook_id} updated with new cover")

        # Step 6: Emit domain event
        await self.event_bus.publish(
            CoverRegeneratedEvent(
                ebook_id=ebook_id,
                title=updated_ebook.title or "Untitled",
                prompt_used=cover_prompt,
            )
        )

        return updated_ebook
