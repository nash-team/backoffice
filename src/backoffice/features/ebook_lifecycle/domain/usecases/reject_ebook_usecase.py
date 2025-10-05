"""Use case for rejecting an ebook."""

import logging

from backoffice.features.ebook_lifecycle.domain.events.ebook_rejected_event import (
    EbookRejectedEvent,
)
from backoffice.features.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.domain.ports.ebook.ebook_port import EbookPort
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class RejectEbookUseCase:
    """Use case for rejecting an ebook (manual review).

    This use case handles the rejection workflow:
    1. Validates ebook status (must be DRAFT or APPROVED)
    2. Updates ebook status to REJECTED
    3. Emits EbookRejectedEvent
    """

    def __init__(self, ebook_repository: EbookPort, event_bus: EventBus):
        """Initialize use case with dependencies.

        Args:
            ebook_repository: Repository for ebook persistence
            event_bus: Event bus for publishing domain events
        """
        self.ebook_repository = ebook_repository
        self.event_bus = event_bus
        logger.info("RejectEbookUseCase initialized")

    async def execute(self, ebook_id: int, reason: str | None = None) -> Ebook:
        """Reject an ebook (manual review decision).

        Args:
            ebook_id: ID of the ebook to reject
            reason: Optional rejection reason

        Returns:
            Updated ebook entity with REJECTED status

        Raises:
            DomainError: If ebook not found or cannot be rejected
        """
        # 1. Load ebook from repository
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise DomainError(
                code=ErrorCode.EBOOK_NOT_FOUND,
                message=f"Ebook with ID {ebook_id} not found",
                actionable_hint="Verify ebook ID",
            )

        # 2. Validate status (must be DRAFT or APPROVED)
        if ebook.status not in [EbookStatus.DRAFT, EbookStatus.APPROVED]:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Cannot reject ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT or APPROVED ebooks can be rejected",
            )

        logger.info(
            f"Rejecting ebook {ebook_id}: '{ebook.title}' "
            f"(reason: {reason or 'No reason provided'})"
        )

        # 3. Update status to REJECTED
        ebook.status = EbookStatus.REJECTED

        # 4. Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)

        # 5. Emit domain event
        await self.event_bus.publish(
            EbookRejectedEvent(
                ebook_id=ebook_id,
                reason=reason or "No reason provided",
                title=updated_ebook.title,
            )
        )

        logger.info(f"✅ Ebook {ebook_id} rejected successfully")
        return updated_ebook
