"""Use case for exporting ebook to Amazon KDP format."""

import logging
from typing import TYPE_CHECKING, cast

from backoffice.features.ebook.export.domain.events.kdp_export_generated_event import (
    KDPExportGeneratedEvent,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    EbookStatus,
    KDPExportConfig,
)
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

if TYPE_CHECKING:
    from backoffice.features.ebook.shared.infrastructure.providers.images.openrouter import (  # noqa: E501
        openrouter_image_provider,
    )
    from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.assembly import (  # noqa: E501
        cover_assembly_provider,
    )

logger = logging.getLogger(__name__)


class ExportToKDPUseCase:
    """Use case for exporting an approved ebook to KDP paperback format."""

    def __init__(
        self,
        ebook_repository: EbookPort,
        event_bus: EventBus,
        image_provider: "openrouter_image_provider.OpenRouterImageProvider | None" = None,
        kdp_assembly_provider: "cover_assembly_provider.KDPAssemblyProvider | None" = None,
    ):
        self.ebook_repository = ebook_repository
        self.event_bus = event_bus
        self.image_provider = image_provider
        self.kdp_assembly_provider = kdp_assembly_provider
        logger.info("ExportToKDPUseCase initialized")

    async def execute(
        self,
        ebook_id: int,
        kdp_config: KDPExportConfig | None = None,
        preview_mode: bool = False,
    ) -> bytes:
        """Export an approved ebook to KDP format.

        Args:
            ebook_id: ID of the ebook to export
            kdp_config: Optional KDP export configuration
            preview_mode: If True, allows DRAFT ebooks (for preview only, not download)

        Returns:
            PDF bytes ready for KDP upload

        Raises:
            DomainError: If ebook not found, not approved, or export fails
        """
        # 1. Load ebook from repository
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise DomainError(
                code=ErrorCode.EBOOK_NOT_FOUND,
                message=f"Ebook with ID {ebook_id} not found",
                actionable_hint="Verify ebook ID",
            )

        # 2. Validate status (must be APPROVED for download, DRAFT allowed for preview)
        if not preview_mode and ebook.status != EbookStatus.APPROVED:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(
                    f"Ebook must be APPROVED to download KDP export "
                    f"(current: {ebook.status.value})"
                ),
                actionable_hint="Only APPROVED ebooks can be downloaded as KDP",
            )

        # For preview mode, allow DRAFT or APPROVED
        if preview_mode and ebook.status not in [EbookStatus.DRAFT, EbookStatus.APPROVED]:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(
                    f"Ebook must be DRAFT or APPROVED to preview KDP "
                    f"(current: {ebook.status.value})"
                ),
                actionable_hint="Only DRAFT or APPROVED ebooks can be previewed",
            )

        # 3. Validate page_count is present
        if not ebook.page_count:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook must have page_count for KDP export",
                actionable_hint="Regenerate the ebook to populate page_count",
            )

        logger.info(
            f"Exporting ebook {ebook_id} to KDP format: '{ebook.title}' ({ebook.page_count} pages)"
        )

        # 4. Use default KDP config if none provided
        if kdp_config is None:
            kdp_config = KDPExportConfig()

        # 4b. Adjust paper type for short books (premium_color requires 24-828 pages)
        if ebook.page_count < 24 and kdp_config.paper_type == "premium_color":
            logger.warning(
                f"Ebook has {ebook.page_count} pages (< 24), "
                f"switching from premium_color to standard_color"
            )
            kdp_config = KDPExportConfig(
                trim_size=kdp_config.trim_size,
                bleed_size=kdp_config.bleed_size,
                paper_type="standard_color",
                include_barcode=kdp_config.include_barcode,
                cover_finish=kdp_config.cover_finish,
                icc_rgb_profile=kdp_config.icc_rgb_profile,
            )

        # 5. Initialize providers if not injected
        if not self.image_provider:
            from backoffice.features.ebook.shared.infrastructure.providers.images.openrouter import (  # noqa: E501
                openrouter_image_provider as or_provider,
            )

            self.image_provider = or_provider.OpenRouterImageProvider()

        if not self.kdp_assembly_provider:
            from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.assembly import (  # noqa: E501
                cover_assembly_provider as kdp_provider,
            )

            self.kdp_assembly_provider = kdp_provider.KDPAssemblyProvider()

        # 6. Get front cover bytes (WITH text - for assembly)
        front_cover_bytes = await self._get_front_cover_bytes(ebook)

        # 7. Get back cover bytes (already generated in coloring_book_strategy)
        logger.info("Extracting existing back cover from ebook structure...")
        back_cover_bytes = await self._get_back_cover_bytes(ebook)

        # 8. Assemble KDP PDF (back + spine + front)
        logger.info("Assembling KDP paperback PDF...")
        kdp_pdf_bytes = cast(
            bytes,
            await self.kdp_assembly_provider.assemble_kdp_paperback(
                ebook=ebook,
                back_cover_bytes=back_cover_bytes,
                front_cover_bytes=front_cover_bytes,
                kdp_config=kdp_config,
            ),
        )

        logger.info(f"✅ KDP export completed: {len(kdp_pdf_bytes)} bytes")

        # 8b. Visual validation against KDP template
        await self._validate_cover_against_template(
            back_cover_bytes=back_cover_bytes,
            front_cover_bytes=front_cover_bytes,
            page_count=ebook.page_count,
        )

        # 9. Emit domain event
        await self.event_bus.publish(
            KDPExportGeneratedEvent(
                ebook_id=ebook_id,
                title=ebook.title or "Untitled",
                file_size_bytes=len(kdp_pdf_bytes),
                preview_mode=preview_mode,
                status=ebook.status.value,
            )
        )

        return kdp_pdf_bytes

    async def _get_front_cover_bytes(self, ebook: Ebook) -> bytes:
        """Extract front cover from ebook structure or bytes."""
        # For now, get the first page from structure_json
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook structure missing pages metadata",
                actionable_hint="Regenerate the ebook",
            )

        pages = ebook.structure_json.get("pages_meta", [])
        if not pages:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="No pages found in ebook structure",
                actionable_hint="Regenerate the ebook",
            )

        # First page is the cover
        cover_page = pages[0]
        import base64

        cover_bytes = base64.b64decode(cover_page["image_data_base64"])
        return cover_bytes

    async def _get_back_cover_bytes(self, ebook: Ebook) -> bytes:
        """Extract back cover from ebook structure (last page).

        The back cover is already generated in coloring_book_strategy.py
        as the last page of the ebook.
        """
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook structure missing pages metadata",
                actionable_hint="Regenerate the ebook",
            )

        pages = ebook.structure_json.get("pages_meta", [])
        if len(pages) < 2:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook must have at least 2 pages (cover + back cover)",
                actionable_hint="Regenerate the ebook",
            )

        # Last page is the back cover
        back_cover_page = pages[-1]
        import base64

        back_cover_bytes = base64.b64decode(back_cover_page["image_data_base64"])
        logger.info(f"✅ Extracted back cover from ebook structure: {len(back_cover_bytes)} bytes")
        return back_cover_bytes

    async def _validate_cover_against_template(
        self,
        back_cover_bytes: bytes,
        front_cover_bytes: bytes,
        page_count: int,
    ) -> None:
        """Validate assembled full cover against official KDP template.

        This validation is informational only (logs warnings, doesn't fail export).

        Args:
            back_cover_bytes: Back cover image bytes
            front_cover_bytes: Front cover image bytes
            page_count: Number of pages for spine calculation
        """
        try:
            from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.visual_validator import (  # noqa: E501
                assemble_full_kdp_cover,
                validate_full_cover_against_template,
            )

            logger.info("🔍 Validating KDP cover against official template...")

            # Assemble full cover (same logic as KDPAssemblyProvider but in PNG)
            full_cover_bytes = assemble_full_kdp_cover(
                back_cover_bytes=back_cover_bytes,
                front_cover_bytes=front_cover_bytes,
                page_count=page_count,
            )

            # Validate against template
            validation_result = validate_full_cover_against_template(full_cover_bytes)

            if validation_result.get("valid"):
                logger.info(f"✅ {validation_result['message']}")
            else:
                logger.warning(f"⚠️ {validation_result['message']}")
                logger.warning(
                    f"   Cover size: {validation_result.get('cover_size')} vs "
                    f"expected: {validation_result.get('expected_size')}"
                )

        except Exception as e:
            # Don't fail export if validation fails - just log warning
            logger.warning(f"⚠️ KDP template validation failed (non-critical): {str(e)}")
