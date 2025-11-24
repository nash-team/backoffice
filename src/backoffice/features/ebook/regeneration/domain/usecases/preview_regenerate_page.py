"""Use case for preview regeneration of a content page without saving to DB."""

import base64
import logging

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.services.page_generation import (
    ContentPageGenerationService,
)

logger = logging.getLogger(__name__)


class PreviewRegeneratePageUseCase:
    """Preview regenerate a content page without saving to DB or storage.

    This generates a new version of a page for preview purposes only.
    The generated image is returned as base64 but NOT saved to DB/storage.
    No PDF rebuild occurs.
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        page_service: ContentPageGenerationService,
    ):
        """Initialize preview regenerate page use case.

        Args:
            ebook_repository: Repository for ebook retrieval
            page_service: Service for page generation
        """
        self.ebook_repository = ebook_repository
        self.page_service = page_service

    async def execute(
        self,
        ebook_id: int,
        page_index: int,
    ) -> dict[str, str | int]:
        """Preview regenerate a specific content page.

        Args:
            ebook_id: ID of the ebook
            page_index: Index of the page to regenerate (1-based, excluding cover)

        Returns:
            Dictionary with:
                - image_base64: Base64-encoded image data
                - page_index: The page index regenerated
                - prompt_used: The prompt used for generation

        Raises:
            DomainError: If ebook not found, not DRAFT, or invalid page index
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
                message=f"Cannot preview regenerate page for ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT ebooks can be modified",
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Cannot preview regenerate page: ebook structure is missing",
                actionable_hint="Please regenerate the entire ebook first",
            )

        pages_meta = ebook.structure_json["pages_meta"]

        # Validate page index (must be between cover and back cover)
        if page_index < 1 or page_index >= len(pages_meta) - 1:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid page index {page_index}",
                actionable_hint=f"Must be between 1 and {len(pages_meta) - 2} (content pages only)",
            )

        logger.info(f"🔄 Preview regenerating CONTENT PAGE {page_index} for ebook {ebook_id}: {ebook.title}")

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

        logger.info(f"✅ Preview page generated: {len(new_page_data)} bytes (not saved)")

        # Return base64-encoded image (NO DB/storage save)
        return {
            "image_base64": base64.b64encode(new_page_data).decode("utf-8"),
            "page_index": page_index,
            "prompt_used": prompt,
        }
