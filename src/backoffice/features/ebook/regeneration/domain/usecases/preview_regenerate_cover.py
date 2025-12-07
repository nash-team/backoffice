"""Use case for preview regeneration of a cover without saving to DB."""

import base64
import logging

from backoffice.features.ebook.shared.domain.entities.ebook import EbookStatus
from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.services.cover_generation import CoverGenerationService

logger = logging.getLogger(__name__)


class PreviewRegenerateCoverUseCase:
    """Preview regenerate a cover without saving to DB or storage.

    This generates a new version of the cover for preview purposes only.
    The generated image is returned as base64 but NOT saved to DB/storage.
    No PDF rebuild occurs.
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        cover_service: CoverGenerationService,
    ):
        """Initialize preview regenerate cover use case.

        Args:
            ebook_repository: Repository for ebook retrieval
            cover_service: Service for cover generation
        """
        self.ebook_repository = ebook_repository
        self.cover_service = cover_service

    async def execute(
        self,
        ebook_id: int,
        current_image_base64: str | None = None,
        custom_prompt: str | None = None,
    ) -> dict[str, str | int]:
        """Preview regenerate the cover.

        Args:
            ebook_id: ID of the ebook
            current_image_base64: Optional latest modal image to chain from
            custom_prompt: Optional custom prompt to use instead of stored/template

        Returns:
            Dictionary with:
                - image_base64: Base64-encoded image data
                - page_index: 0 (cover index)
                - prompt_used: The prompt used for generation

        Raises:
            DomainError: If ebook not found or not DRAFT
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
                message=f"Cannot preview regenerate cover for ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT ebooks can be modified",
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Cannot preview regenerate cover: ebook structure is missing",
                actionable_hint="Please regenerate the entire ebook first",
            )

        pages_meta = ebook.structure_json["pages_meta"]

        logger.info(f"🔄 Preview regenerating COVER for ebook {ebook_id}: {ebook.title}")

        # Determine prompt to use
        # Priority: custom_prompt > stored prompt > build from theme
        if custom_prompt:
            prompt = custom_prompt
            logger.info(f"Using CUSTOM prompt: {prompt[:100]}...")
        elif pages_meta[0].get("prompt"):
            prompt = pages_meta[0]["prompt"]
            logger.info(f"Using STORED prompt: {prompt[:100]}...")
        else:
            # Fallback: build cover prompt from theme
            prompt = self._build_cover_prompt_from_theme(ebook)
            logger.info(f"Using THEME-based prompt: {prompt[:100]}...")

        # Load workflow params from YAML theme
        from backoffice.features.ebook.shared.domain.services.workflow_helper import (
            load_workflow_params,
        )
        from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
            ThemeRepository,
        )

        theme_repo = ThemeRepository()
        workflow_params = load_workflow_params(
            theme_id=ebook.theme_id or "dinosaurs",
            image_type="cover",
            themes_directory=theme_repo.themes_directory,
        )

        # Chain from modal-provided image if available
        if current_image_base64:
            workflow_params = {
                **workflow_params,
                "initial_image_base64": current_image_base64,
            }

        # Generate new cover with color
        cover_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.COLOR,
        )

        new_cover_data = await self.cover_service.generate_cover(
            prompt=prompt,
            spec=cover_spec,
            seed=None,  # Random seed for variety
            workflow_params=workflow_params,
        )

        logger.info(f"✅ Preview cover generated: {len(new_cover_data)} bytes (not saved)")

        # Return base64-encoded image (NO DB/storage save)
        return {
            "image_base64": base64.b64encode(new_cover_data).decode("utf-8"),
            "page_index": 0,
            "prompt_used": prompt,
        }

    def _build_cover_prompt_from_theme(self, ebook) -> str:
        """Build cover prompt from theme configuration.

        Args:
            ebook: Ebook entity with theme_id

        Returns:
            Cover prompt string
        """
        import yaml

        from backoffice.config import ConfigLoader
        from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
            ThemeRepository,
        )

        theme_repo = ThemeRepository()
        config = ConfigLoader()

        # Get the template key based on provider
        template_key = config.get_template_key_for_type("cover")

        # Load theme YAML
        theme_file = theme_repo.themes_directory / f"{ebook.theme_id}.yml"
        if not theme_file.exists():
            return f"Coloring book cover for {ebook.title}"

        with theme_file.open("r", encoding="utf-8") as f:
            theme_data = yaml.safe_load(f)

        cover_template = theme_data.get("cover_templates", {}).get(template_key, {})

        # Check if we have a direct prompt
        if "prompt" in cover_template:
            return str(cover_template["prompt"])

        # Fallback
        return f"Coloring book cover for {ebook.title}"
