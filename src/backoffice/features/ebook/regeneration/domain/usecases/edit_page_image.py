"""Use case for editing a content page image with targeted corrections."""

import base64
import logging

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.ports.image_edit_port import ImageEditPort

logger = logging.getLogger(__name__)


class EditPageImageUseCase:
    """Edit a content page image with targeted corrections without saving to DB.

    This applies specific corrections to an existing page image (e.g., "replace 5 toes with 3").
    The edited image is returned as base64 but NOT saved to DB/storage.
    No PDF rebuild occurs - this is preview only.
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        image_edit_port: ImageEditPort,
    ):
        """Initialize edit page image use case.

        Args:
            ebook_repository: Repository for ebook retrieval
            image_edit_port: Port for image editing operations
        """
        self.ebook_repository = ebook_repository
        self.image_edit_port = image_edit_port

    async def execute(
        self,
        ebook_id: int,
        page_index: int,
        edit_prompt: str,
    ) -> dict[str, str | int]:
        """Edit a specific content page image with targeted corrections.

        Args:
            ebook_id: ID of the ebook
            page_index: Index of the page to edit (1-based, excluding cover)
            edit_prompt: Text instructions for editing (e.g., "replace 5 toes with 3")

        Returns:
            Dictionary with:
                - image_base64: Base64-encoded edited image data
                - page_index: The page index edited
                - edit_prompt_used: The edit prompt used

        Raises:
            DomainError: If ebook not found, not DRAFT, invalid page index, or edit fails
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
                message=f"Cannot edit page for ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT ebooks can be modified",
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Cannot edit page: ebook structure is missing",
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

        # Validate edit prompt
        if not edit_prompt or not edit_prompt.strip():
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Edit prompt cannot be empty",
                actionable_hint="Provide instructions for editing the image",
            )

        logger.info(f"✏️ Editing CONTENT PAGE {page_index} for ebook {ebook_id}: {ebook.title}")
        logger.info(f"Edit prompt: {edit_prompt[:100]}...")

        # Step 1: Load current page image from structure_json
        page_meta = pages_meta[page_index]
        if "image_data_base64" not in page_meta:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Page {page_index} does not have an image",
                actionable_hint="Ensure the page has been generated first",
            )

        current_image_base64 = page_meta["image_data_base64"]
        current_image_bytes = base64.b64decode(current_image_base64)

        logger.info(f"Loaded current page image: {len(current_image_bytes)} bytes")

        # Step 2: Check if provider is available
        if not self.image_edit_port.is_available():
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="Image edit provider is not available",
                actionable_hint="Check provider configuration (Gemini API key or ComfyUI server)",
            )

        # Step 3: Edit the image with the edit prompt
        page_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.BLACK_WHITE,
        )

        edited_image_bytes = await self.image_edit_port.edit_image(
            image=current_image_bytes,
            edit_prompt=edit_prompt,
            spec=page_spec,
        )

        logger.info(f"✅ Page edited: {len(edited_image_bytes)} bytes (not saved)")

        # Return base64-encoded image (NO DB/storage save)
        return {
            "image_base64": base64.b64encode(edited_image_bytes).decode("utf-8"),
            "page_index": page_index,
            "edit_prompt_used": edit_prompt,
        }
