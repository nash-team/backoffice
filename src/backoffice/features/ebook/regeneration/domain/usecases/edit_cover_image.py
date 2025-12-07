"""Use case for editing a cover image with targeted corrections."""

import base64
import logging

from backoffice.features.ebook.shared.domain.entities.ebook import EbookStatus
from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.ports.image_edit_port import ImageEditPort

logger = logging.getLogger(__name__)


class EditCoverImageUseCase:
    """Edit a cover image with targeted corrections without saving to DB.

    This applies specific corrections to an existing cover image (e.g., "replace 5 toes with 3").
    The edited image is returned as base64 but NOT saved to DB/storage.
    No PDF rebuild occurs - this is preview only.
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        image_edit_port: ImageEditPort,
    ):
        """Initialize edit cover image use case.

        Args:
            ebook_repository: Repository for ebook retrieval
            image_edit_port: Port for image editing operations
        """
        self.ebook_repository = ebook_repository
        self.image_edit_port = image_edit_port

    async def execute(
        self,
        ebook_id: int,
        edit_prompt: str,
        current_image_base64: str | None = None,
    ) -> dict[str, str | int]:
        """Edit the cover image with targeted corrections.

        Args:
            ebook_id: ID of the ebook
            edit_prompt: Text instructions for editing (e.g., "replace 5 toes with 3")
            current_image_base64: Optional base64 image from the modal (latest preview)

        Returns:
            Dictionary with:
                - image_base64: Base64-encoded edited image data
                - page_index: 0 (cover index)
                - edit_prompt_used: The edit prompt used

        Raises:
            DomainError: If ebook not found, not DRAFT, or edit fails
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
                message=f"Cannot edit cover for ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT ebooks can be modified",
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Cannot edit cover: ebook structure is missing",
                actionable_hint="Please regenerate the entire ebook first",
            )

        pages_meta = ebook.structure_json["pages_meta"]

        # Validate edit prompt
        if not edit_prompt or not edit_prompt.strip():
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Edit prompt cannot be empty",
                actionable_hint="Provide instructions for editing the image",
            )

        logger.info(f"✏️ Editing COVER for ebook {ebook_id}: {ebook.title}")
        logger.info(f"Edit prompt: {edit_prompt[:100]}...")

        # Load current cover image, preferring the modal-provided preview when available
        if current_image_base64:
            try:
                current_image_bytes = base64.b64decode(current_image_base64)
            except Exception as exc:
                raise DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid base64 image provided by the modal",
                    actionable_hint="Retry from the latest preview image",
                ) from exc
        else:
            cover_meta = pages_meta[0]  # Cover is always at index 0
            if "image_data_base64" not in cover_meta:
                raise DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Cover does not have an image",
                    actionable_hint="Ensure the cover has been generated first",
                )
            current_image_bytes = base64.b64decode(cover_meta["image_data_base64"])

        logger.info(f"Loaded current cover image: {len(current_image_bytes)} bytes")

        # Check if provider is available
        if not self.image_edit_port.is_available():
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="Image edit provider is not available",
                actionable_hint="Check provider configuration (Gemini API key or ComfyUI server)",
            )

        # Edit the image with the edit prompt
        # Cover uses COLOR mode (not BLACK_WHITE like content pages)
        cover_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.COLOR,
        )

        edited_image_bytes = await self.image_edit_port.edit_image(
            image_bytes=current_image_bytes,
            edit_prompt=edit_prompt,
            spec=cover_spec,
        )

        logger.info(f"✅ Cover edited: {len(edited_image_bytes)} bytes (not saved)")

        # Return base64-encoded image (NO DB/storage save)
        return {
            "image_base64": base64.b64encode(edited_image_bytes).decode("utf-8"),
            "page_index": 0,
            "edit_prompt_used": edit_prompt,
        }
