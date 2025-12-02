"""Use case for adding AI-generated coloring pages to an existing ebook."""

import base64
import logging
from dataclasses import dataclass
from typing import Literal

from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.constants import MAX_PAGES
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.services.page_generation import (
    ContentPageGenerationService,
)

logger = logging.getLogger(__name__)


@dataclass
class AddNewPagesResult:
    """Result of adding new pages to an ebook."""

    ebook: Ebook
    pages_added: int
    total_pages: int
    limit_reached: bool
    message: str


class AddNewPagesUseCase:
    """Add AI-generated coloring pages to an existing ebook.

    Pages are generated using the same theme/style/seed as the original ebook
    and inserted before the back cover.
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        page_service: ContentPageGenerationService,
        regeneration_service: RegenerationService,
    ):
        """Initialize the use case.

        Args:
            ebook_repository: Repository for ebook persistence
            page_service: Service for page generation
            regeneration_service: Service for PDF reassembly
        """
        self.ebook_repository = ebook_repository
        self.page_service = page_service
        self.regeneration_service = regeneration_service

    async def execute(self, ebook_id: int, count: int) -> AddNewPagesResult:
        """Add new AI-generated pages to an ebook.

        Args:
            ebook_id: ID of the ebook
            count: Number of pages to add (will be adjusted if limit reached)

        Returns:
            AddNewPagesResult with pages added count and limit info

        Raises:
            DomainError: If ebook not found, not DRAFT, or no structure
        """
        # 1. Load ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise DomainError(
                code=ErrorCode.EBOOK_NOT_FOUND,
                message=f"Ebook with ID {ebook_id} not found",
                actionable_hint="Verify ebook ID",
            )

        # 2. Validate DRAFT status
        if ebook.status != EbookStatus.DRAFT:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Cannot add pages to ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT ebooks can be modified",
            )

        # 3. Validate structure exists
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook has no structure - cannot add pages",
                actionable_hint="Generate ebook first",
            )

        pages_meta = ebook.structure_json["pages_meta"]
        current_total = len(pages_meta)
        current_interior = current_total - 2  # Exclude cover and back cover

        # 4. Calculate remaining capacity
        max_interior = MAX_PAGES
        remaining_capacity = max_interior - current_interior

        if remaining_capacity <= 0:
            return AddNewPagesResult(
                ebook=ebook,
                pages_added=0,
                total_pages=current_total,
                limit_reached=True,
                message=f"Maximum {MAX_PAGES} pages atteint",
            )

        # 5. Adjust count if exceeds capacity (partial addition)
        limit_reached = False
        if count > remaining_capacity:
            count = remaining_capacity
            limit_reached = True

        logger.info(f"Adding {count} new pages to ebook {ebook_id} " f"(current: {current_interior}, max: {max_interior})")

        # 6. Load theme configuration
        from backoffice.features.ebook.shared.domain.services.workflow_helper import (
            build_page_prompt_from_yaml,
            load_workflow_params,
        )
        from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
            ThemeRepository,
        )

        theme_repo = ThemeRepository()
        theme_id = ebook.theme_id or "dinosaurs"
        audience: Literal["children", "adults"] = "adults" if ebook.audience == "adults" else "children"

        # Load workflow params once (same for all pages)
        workflow_params = load_workflow_params(
            theme_id=theme_id,
            image_type="coloring_page",
            themes_directory=theme_repo.themes_directory,
        )

        # Page spec for B&W coloring pages
        page_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.BLACK_WHITE,
        )

        # 7. Extract back cover to re-add after new pages
        back_cover = pages_meta.pop()

        # 8. Generate and add new pages
        last_page_number = pages_meta[-1]["page_number"] if pages_meta else 0
        new_total_content = current_interior + count

        for i in range(count):
            page_index = current_interior + i  # 0-based index for new pages
            page_number = last_page_number + i + 1

            # Build prompt for this page
            prompt = build_page_prompt_from_yaml(
                theme_id=theme_id,
                page_index=page_index,
                total_pages=new_total_content,
                themes_directory=theme_repo.themes_directory,
                seed=42,
                audience=audience,
            )

            logger.info(f"Generating page {page_number} with prompt: {prompt[:80]}...")

            # Generate page
            page_data = await self.page_service.generate_single_page(
                prompt=prompt,
                spec=page_spec,
                seed=None,  # Random seed for variety
                workflow_params=workflow_params,
            )

            # Add to pages_meta
            pages_meta.append(
                {
                    "page_number": page_number,
                    "title": f"Page {page_number}",
                    "image_data_base64": base64.b64encode(page_data).decode("utf-8"),
                    "image_format": "PNG",
                    "color_mode": "BLACK_WHITE",
                }
            )
            logger.info(f"  Added page {page_number} ({len(page_data)} bytes)")

        # 9. Re-add back cover as last page
        back_cover["page_number"] = pages_meta[-1]["page_number"] + 1
        pages_meta.append(back_cover)

        # 10. Update ebook structure and page count
        ebook.structure_json["pages_meta"] = pages_meta
        ebook.page_count = len(pages_meta)

        # 11. Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)

        # 12. Reassemble PDF
        logger.info(f"Reassembling PDF with {len(pages_meta)} pages...")
        assembled_pages = self._convert_pages_meta_to_assembled_pages(pages_meta)

        await self.regeneration_service.rebuild_and_upload_pdf(
            ebook=updated_ebook,
            assembled_pages=assembled_pages,
            ebook_repository=self.ebook_repository,
            filename_suffix="pages_added",
        )

        # 13. Build result
        message = f"{count} page(s) ajoutée(s)"
        if limit_reached:
            message += f" - Maximum {MAX_PAGES} pages atteint"

        logger.info(f"Ebook {ebook_id}: {message} (total: {updated_ebook.page_count})")

        return AddNewPagesResult(
            ebook=updated_ebook,
            pages_added=count,
            total_pages=updated_ebook.page_count or len(pages_meta),
            limit_reached=limit_reached,
            message=message,
        )

    def _convert_pages_meta_to_assembled_pages(self, pages_meta: list[dict]) -> list[AssembledPage]:
        """Convert pages_meta to AssembledPage objects for PDF assembly."""
        assembled_pages = []
        for page_data in pages_meta:
            image_bytes = base64.b64decode(page_data["image_data_base64"])
            assembled_pages.append(
                AssembledPage(
                    page_number=page_data["page_number"],
                    title=page_data.get("title", f"Page {page_data['page_number']}"),
                    image_data=image_bytes,
                    image_format=page_data.get("image_format", "PNG"),
                )
            )
        return assembled_pages
