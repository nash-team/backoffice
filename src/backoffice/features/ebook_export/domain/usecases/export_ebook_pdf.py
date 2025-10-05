"""Use case for exporting ebook PDFs from database."""

import logging

from backoffice.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.domain.ports.ebook.ebook_port import EbookPort
from backoffice.features.ebook_export.domain.events.ebook_exported_event import EbookExportedEvent
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class ExportEbookPdfUseCase:
    """Use case for exporting raw ebook PDFs from database.

    This use case handles:
    - Retrieving PDF bytes from database
    - Validating ebook exists
    - Emitting export event for tracking
    """

    def __init__(self, ebook_repository: EbookPort, event_bus: EventBus):
        """Initialize use case with dependencies.

        Args:
            ebook_repository: Repository for ebook access
            event_bus: Event bus for publishing domain events
        """
        self.ebook_repository = ebook_repository
        self.event_bus = event_bus

    async def execute(self, ebook_id: int) -> bytes:
        """Export ebook PDF from database.

        Args:
            ebook_id: ID of the ebook to export

        Returns:
            PDF bytes

        Raises:
            DomainError: If ebook not found or PDF not available
        """
        logger.info(f"📥 Exporting PDF for ebook {ebook_id}")

        # Step 1: Validate ebook exists
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise DomainError(
                code=ErrorCode.EBOOK_NOT_FOUND,
                message=f"Ebook with id {ebook_id} not found",
                actionable_hint="Verify the ebook ID is correct",
            )

        # Step 2: Get PDF bytes from repository
        pdf_bytes = await self.ebook_repository.get_ebook_bytes(ebook_id)
        if not pdf_bytes:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="PDF not found - may have been deleted after approval",
                actionable_hint=(
                    "Try regenerating the ebook or check if it was approved and removed"
                ),
            )

        logger.info(f"✅ PDF retrieved: {len(pdf_bytes)} bytes")

        # Step 3: Emit domain event
        await self.event_bus.publish(
            EbookExportedEvent(
                ebook_id=ebook_id,
                title=ebook.title or "Untitled",
                file_size_bytes=len(pdf_bytes),
                export_format="pdf",
            )
        )

        return pdf_bytes
