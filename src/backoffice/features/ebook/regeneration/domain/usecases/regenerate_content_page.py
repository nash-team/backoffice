"""Use case for regenerating a single content/coloring page."""

import base64
import logging

from backoffice.features.ebook.regeneration.domain.events.content_page_regenerated_event import (
    ContentPageRegeneratedEvent,
)
from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook
from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.services.ebook_validator import EbookValidator
from backoffice.features.ebook.shared.domain.services.page_generation import (
    ContentPageGenerationService,
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
    ) -> Ebook:
        """Regenerate a specific content page of an ebook.

        Args:
            ebook_id: ID of the ebook
            page_index: Index of the page to regenerate (1-based, excluding cover)

        Returns:
            Updated ebook with regenerated page

        Raises:
            DomainError: If ebook not found, not DRAFT, missing structure, or invalid page index
        """
        # Validate ebook (exists + DRAFT status + has structure)
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        ebook = EbookValidator.validate_for_approval(ebook, ebook_id)
        if ebook.structure_json is None:  # pragma: no cover — guaranteed by validator
            raise DomainError(code=ErrorCode.VALIDATION_ERROR, message="Ebook has no structure data", actionable_hint="Regenerate the ebook first")

        pages_meta = ebook.structure_json["pages_meta"]

        # Validate page index (must be between cover and back cover)
        if page_index < 1 or page_index >= len(pages_meta) - 1:
            raise ValueError(f"Invalid page index {page_index}. Must be between 1 and {len(pages_meta) - 2} (content pages only).")

        logger.info(f"🔄 Regenerating CONTENT PAGE {page_index} for ebook {ebook_id}: {ebook.title}")

        # Step 1: Build page prompt from YAML theme
        from backoffice.features.ebook.shared.domain.services.workflow_helper import (
            build_page_prompt_from_yaml,
            load_workflow_params,
        )
        from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
            ThemeRepository,
        )

        theme_repo = ThemeRepository()

        # Calculate total pages excluding cover and back cover
        total_content_pages = len(pages_meta) - 2

        prompt = build_page_prompt_from_yaml(
            theme_id=ebook.theme_id or "dinosaurs",
            page_index=page_index - 1,  # Convert to 0-based index
            total_pages=total_content_pages,
            themes_directory=theme_repo.themes_directory,
            seed=42,  # Default seed for reproducibility
            audience="adults" if ebook.audience == "adults" else "children",
        )
        logger.info(f"Using YAML-based prompt: {prompt[:100]}...")

        # Step 2: Load workflow params from YAML theme
        workflow_params = load_workflow_params(
            theme_id=ebook.theme_id or "dinosaurs",
            image_type="coloring_page",
            themes_directory=theme_repo.themes_directory,
        )

        # Step 3: Generate new page with B&W coloring style
        page_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.BLACK_WHITE,
        )

        new_page_data = await self.page_service.generate_single_page(
            prompt=prompt,
            spec=page_spec,
            seed=None,  # Random seed for variety
            workflow_params=workflow_params,
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

        # Step 3: Update structure_json with new page (include prompt for edit modal)
        updated_pages_meta = pages_meta.copy()
        updated_pages_meta[page_index] = {
            "page_number": page_index,
            "title": f"Page {page_index}",
            "image_format": "PNG",
            "image_data_base64": base64.b64encode(new_page_data).decode(),
            "prompt": prompt,  # Store prompt for regeneration/editing
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
            )
        )

        return updated_ebook
