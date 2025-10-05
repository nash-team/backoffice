"""Use case for approving an ebook and uploading it to storage."""

import logging

from backoffice.features.ebook_lifecycle.domain.events.ebook_approved_event import (
    EbookApprovedEvent,
)
from backoffice.features.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.domain.ports.ebook.ebook_port import EbookPort
from backoffice.features.shared.domain.ports.file_storage_port import FileStoragePort
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class ApproveEbookUseCase:
    """Use case for approving an ebook and uploading it to Drive.

    This use case handles the complete approval workflow:
    1. Validates ebook status (must be DRAFT)
    2. Uploads PDF to Google Drive
    3. Updates ebook status to APPROVED
    4. Emits EbookApprovedEvent
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
        """Approve an ebook and upload it to storage.

        Args:
            ebook_id: ID of the ebook to approve

        Returns:
            Updated ebook entity with APPROVED status and Drive ID

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

        # 4. Get ebook bytes from repository (should be stored during generation)
        ebook_bytes = await self.ebook_repository.get_ebook_bytes(ebook_id)
        if not ebook_bytes:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook bytes not found, cannot upload to storage",
                actionable_hint="Regenerate the ebook",
            )

        logger.info(f"Approving ebook {ebook_id}: '{ebook.title}' ({len(ebook_bytes)} bytes)")

        # 5. Upload to Drive
        try:
            filename = f"{ebook.title}.pdf"
            metadata = {
                "title": ebook.title,
                "author": ebook.author,
                "format": "pdf",
            }

            storage_result = await self.file_storage.upload_ebook(
                file_bytes=ebook_bytes,
                filename=filename,
                metadata=metadata,
            )

            logger.info(
                f"✅ Ebook uploaded to Drive: {storage_result.get('storage_id')} "
                f"(URL: {storage_result.get('storage_url')})"
            )

            # 6. Update ebook with Drive info and APPROVED status
            ebook.drive_id = storage_result.get("storage_id")
            ebook.preview_url = storage_result.get("storage_url")
            ebook.status = EbookStatus.APPROVED

            # 7. Save updated ebook
            updated_ebook = await self.ebook_repository.save(ebook)

            # 8. Emit domain event
            await self.event_bus.publish(
                EbookApprovedEvent(
                    ebook_id=ebook_id,
                    drive_id=updated_ebook.drive_id,
                    storage_url=updated_ebook.preview_url,
                    title=updated_ebook.title,
                )
            )

            logger.info(f"✅ Ebook {ebook_id} approved and uploaded successfully")
            return updated_ebook

        except Exception as e:
            logger.error(f"❌ Failed to upload ebook {ebook_id} to storage: {e}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Failed to upload ebook to storage: {str(e)}",
                actionable_hint="Check Drive API credentials and quota",
            ) from e
