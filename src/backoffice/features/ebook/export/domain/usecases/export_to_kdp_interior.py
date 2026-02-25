"""Use case for exporting ebook interior to Amazon KDP manuscript format."""

import logging
from typing import TYPE_CHECKING

from backoffice.features.ebook.export.domain.events.kdp_export_generated_event import (
    KDPExportGeneratedEvent,
)
from backoffice.features.ebook.export.domain.services.kdp_export_validator import (
    KdpExportValidator,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    KDPExportConfig,
)
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
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
        kdp_interior_assembly_provider: ("interior_assembly_provider.KDPInteriorAssemblyProvider | None") = None,
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
        # 1. Load and validate ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        ebook = KdpExportValidator.validate_for_export(ebook, ebook_id, preview_mode, export_type="KDP interior")

        logger.info(f"Exporting ebook {ebook_id} interior to KDP format: '{ebook.title}' ({ebook.page_count} pages)")

        # 2. Adjust KDP config for short books if needed
        kdp_config = KdpExportValidator.adjust_config_for_short_books(ebook, kdp_config)

        # 3. Initialize provider if not injected
        if not self.kdp_interior_assembly_provider:
            from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.assembly import (
                interior_assembly_provider as kdp_provider,
            )

            self.kdp_interior_assembly_provider = kdp_provider.KDPInteriorAssemblyProvider()

        # 4. Assemble KDP interior PDF (content pages only, no cover/back)
        logger.info("Assembling KDP interior/manuscript PDF...")
        kdp_interior_pdf_bytes = await self.kdp_interior_assembly_provider.assemble_kdp_interior(
            ebook=ebook,
            kdp_config=kdp_config,
        )

        logger.info(f"✅ KDP interior export completed: {len(kdp_interior_pdf_bytes)} bytes")

        # 5. Emit domain event
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
