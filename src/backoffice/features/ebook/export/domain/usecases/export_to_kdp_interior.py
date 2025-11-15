"""Use case for exporting ebook interior to Amazon KDP manuscript format."""

import logging
from typing import TYPE_CHECKING

from backoffice.features.ebook.export.domain.events.kdp_export_generated_event import (
    KDPExportGeneratedEvent,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    EbookStatus,
    KDPExportConfig,
)
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

if TYPE_CHECKING:
    from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.assembly import (
        interior_assembly_provider,
    )

logger = logging.getLogger(__name__)


class ExportToKDPInteriorUseCase:
    """Use case for exporting an approved ebook interior to KDP manuscript format."""

    def __init__(
        self,
        ebook_repository: EbookPort,
        event_bus: EventBus,
        kdp_interior_assembly_provider: (
            "interior_assembly_provider.KDPInteriorAssemblyProvider | None"
        ) = None,
    ):
        self.ebook_repository = ebook_repository
        self.event_bus = event_bus
        self.kdp_interior_assembly_provider = kdp_interior_assembly_provider
        logger.info("ExportToKDPInteriorUseCase initialized")

    async def execute(
        self,
        ebook_id: int,
        kdp_config: KDPExportConfig | None = None,
        preview_mode: bool = False,
    ) -> bytes:
        """Export an approved ebook interior to KDP manuscript format.

        Args:
            ebook_id: ID of the ebook to export
            kdp_config: Optional KDP export configuration
            preview_mode: If True, allows DRAFT ebooks (for preview only, not download)

        Returns:
            PDF bytes ready for KDP interior/manuscript upload

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
                    f"Ebook must be APPROVED to download KDP interior "
                    f"(current: {ebook.status.value})"
                ),
                actionable_hint="Only APPROVED ebooks can be downloaded as KDP interior",
            )

        # For preview mode, allow DRAFT or APPROVED
        if preview_mode and ebook.status not in [EbookStatus.DRAFT, EbookStatus.APPROVED]:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(
                    f"Ebook must be DRAFT or APPROVED to preview KDP interior "
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
            f"Exporting ebook {ebook_id} interior to KDP format: "
            f"'{ebook.title}' ({ebook.page_count} pages)"
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
                paper_type="standard_color",  # Use standard_color for books < 24 pages
                include_barcode=kdp_config.include_barcode,
                cover_finish=kdp_config.cover_finish,
                icc_rgb_profile=kdp_config.icc_rgb_profile,
                icc_cmyk_profile=kdp_config.icc_cmyk_profile,
            )

        # 5. Initialize provider if not injected
        if not self.kdp_interior_assembly_provider:
            from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.assembly import (
                interior_assembly_provider as kdp_provider,
            )

            self.kdp_interior_assembly_provider = kdp_provider.KDPInteriorAssemblyProvider()

        # 6. Assemble KDP interior PDF (content pages only, no cover/back)
        logger.info("Assembling KDP interior/manuscript PDF...")
        kdp_interior_pdf_bytes = await self.kdp_interior_assembly_provider.assemble_kdp_interior(
            ebook=ebook,
            kdp_config=kdp_config,
        )

        logger.info(f"✅ KDP interior export completed: {len(kdp_interior_pdf_bytes)} bytes")

        # 7. Emit domain event
        await self.event_bus.publish(
            KDPExportGeneratedEvent(
                ebook_id=ebook_id,
                title=ebook.title or "Untitled",
                file_size_bytes=len(kdp_interior_pdf_bytes),
                preview_mode=preview_mode,
                status=ebook.status.value,
            )
        )

        return kdp_interior_pdf_bytes
