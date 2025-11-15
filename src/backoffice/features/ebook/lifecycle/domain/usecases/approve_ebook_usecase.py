"""Use case for approving an ebook and uploading KDP files to storage."""

import logging

from backoffice.features.ebook.export.domain.usecases.export_to_kdp import ExportToKDPUseCase
from backoffice.features.ebook.export.domain.usecases.export_to_kdp_interior import (
    ExportToKDPInteriorUseCase,
)
from backoffice.features.ebook.lifecycle.domain.events.ebook_approved_event import (
    EbookApprovedEvent,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.ports.file_storage_port import FileStoragePort
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class ApproveEbookUseCase:
    """Use case for approving an ebook and uploading KDP files to Drive.

    This use case handles the complete approval workflow:
    1. Validates ebook status (must be DRAFT)
    2. Generates KDP Cover PDF (back + spine + front)
    3. Generates KDP Interior PDF (content pages only)
    4. Uploads both PDFs to Google Drive
    5. Updates ebook status to APPROVED with Drive IDs
    6. Emits EbookApprovedEvent
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        file_storage: FileStoragePort,
        event_bus: EventBus,
    ):
        """Initialize use case with dependencies.

        Args:
            ebook_repository: Repository for ebook persistence
            file_storage: File storage service (e.g., Google Drive)
            event_bus: Event bus for publishing domain events
        """
        self.ebook_repository = ebook_repository
        self.file_storage = file_storage
        self.event_bus = event_bus
        logger.info("ApproveEbookUseCase initialized")

    async def execute(self, ebook_id: int) -> Ebook:
        """Approve an ebook and upload KDP files to storage.

        Args:
            ebook_id: ID of the ebook to approve

        Returns:
            Updated ebook entity with APPROVED status and Drive IDs for Cover and Interior

        Raises:
            DomainError: If ebook not found, not in DRAFT status, or upload fails
        """
        # 1. Load ebook from repository
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise DomainError(
                code=ErrorCode.EBOOK_NOT_FOUND,
                message=f"Ebook with ID {ebook_id} not found",
                actionable_hint="Verify ebook ID",
            )

        # 2. Validate status (must be DRAFT)
        if ebook.status != EbookStatus.DRAFT:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Ebook must be in DRAFT status to approve (current: {ebook.status.value})",
                actionable_hint="Only DRAFT ebooks can be approved",
            )

        # 3. Check storage availability
        if not self.file_storage.is_available():
            raise DomainError(
                code=ErrorCode.PROVIDER_UNAVAILABLE,
                message="File storage service not available",
                actionable_hint="Check Drive credentials and configuration",
            )

        logger.info(f"Approving ebook {ebook_id}: '{ebook.title}'")

        # 4. Generate KDP Cover PDF (back + spine + front)
        try:
            logger.info("Generating KDP Cover PDF...")
            export_kdp_use_case = ExportToKDPUseCase(
                ebook_repository=self.ebook_repository, event_bus=self.event_bus
            )
            cover_pdf_bytes = await export_kdp_use_case.execute(
                ebook_id=ebook_id,
                preview_mode=True,  # Allow DRAFT during approval
            )
            logger.info(f"✅ KDP Cover PDF generated: {len(cover_pdf_bytes)} bytes")
        except Exception as e:
            logger.error(f"❌ Failed to generate KDP Cover PDF: {e}")
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Failed to generate KDP Cover PDF: {str(e)}",
                actionable_hint="Ensure ebook has valid cover and back cover",
            ) from e

        # 5. Generate KDP Interior PDF (content pages only)
        try:
            logger.info("Generating KDP Interior PDF...")
            export_interior_use_case = ExportToKDPInteriorUseCase(
                ebook_repository=self.ebook_repository, event_bus=self.event_bus
            )
            interior_pdf_bytes = await export_interior_use_case.execute(
                ebook_id=ebook_id,
                preview_mode=True,  # Allow DRAFT during approval
            )
            logger.info(f"✅ KDP Interior PDF generated: {len(interior_pdf_bytes)} bytes")
        except Exception as e:
            logger.error(f"❌ Failed to generate KDP Interior PDF: {e}")
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Failed to generate KDP Interior PDF: {str(e)}",
                actionable_hint="Ensure ebook has valid content pages",
            ) from e

        # 6. Upload KDP Cover to Drive
        try:
            cover_filename = f"{ebook.title}_Cover_KDP.pdf"
            cover_metadata = {
                "title": f"{ebook.title} - Cover KDP",
                "author": ebook.author,
                "format": "pdf",
            }

            cover_result = await self.file_storage.upload_ebook(
                file_bytes=cover_pdf_bytes,
                filename=cover_filename,
                metadata=cover_metadata,
            )

            logger.info(
                f"✅ KDP Cover uploaded to Drive: {cover_result.get('storage_id')} "
                f"(URL: {cover_result.get('storage_url')})"
            )
        except Exception as e:
            logger.error(f"❌ Failed to upload KDP Cover to storage: {e}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Failed to upload KDP Cover to storage: {str(e)}",
                actionable_hint="Check Drive API credentials and quota",
            ) from e

        # 7. Upload KDP Interior to Drive
        try:
            interior_filename = f"{ebook.title}_Interior_KDP.pdf"
            interior_metadata = {
                "title": f"{ebook.title} - Interior KDP",
                "author": ebook.author,
                "format": "pdf",
            }

            interior_result = await self.file_storage.upload_ebook(
                file_bytes=interior_pdf_bytes,
                filename=interior_filename,
                metadata=interior_metadata,
            )

            logger.info(
                f"✅ KDP Interior uploaded to Drive: {interior_result.get('storage_id')} "
                f"(URL: {interior_result.get('storage_url')})"
            )
        except Exception as e:
            logger.error(f"❌ Failed to upload KDP Interior to storage: {e}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Failed to upload KDP Interior to storage: {str(e)}",
                actionable_hint="Check Drive API credentials and quota",
            ) from e

        # 8. Update ebook with Drive IDs and APPROVED status
        ebook.drive_id_cover = cover_result.get("storage_id")
        ebook.drive_id_interior = interior_result.get("storage_id")
        ebook.status = EbookStatus.APPROVED

        # 9. Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)

        # 10. Emit domain event
        await self.event_bus.publish(
            EbookApprovedEvent(
                ebook_id=ebook_id,
                drive_id=updated_ebook.drive_id_cover,  # Use cover ID as primary
                storage_url=cover_result.get("storage_url"),
                title=updated_ebook.title,
            )
        )

        logger.info(
            f"✅ Ebook {ebook_id} approved: 2 KDP files uploaded to Drive "
            f"(Cover: {ebook.drive_id_cover}, Interior: {ebook.drive_id_interior})"
        )
        return updated_ebook
