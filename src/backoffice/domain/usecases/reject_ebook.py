"""Use case for rejecting an ebook."""

import logging

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.domain.ports.ebook.ebook_port import EbookPort

logger = logging.getLogger(__name__)


class RejectEbookUseCase:
    """Use case for rejecting an ebook (manual review)."""

    def __init__(self, ebook_repository: EbookPort):
        self.ebook_repository = ebook_repository
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

        logger.info(f"✅ Ebook {ebook_id} rejected successfully")
        return updated_ebook
