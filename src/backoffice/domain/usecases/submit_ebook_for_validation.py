"""Use case for submitting an ebook for validation (DRAFT → PENDING transition)"""

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.ports.ebook.ebook_port import EbookPort


class SubmitEbookForValidationUseCase:
    """Submit an ebook for validation, transitioning from DRAFT to PENDING status"""

    def __init__(self, ebook_repository: EbookPort):
        self.ebook_repository = ebook_repository

    async def execute(self, ebook_id: int) -> Ebook:
        """
        Submit an ebook for validation.

        Args:
            ebook_id: ID of the ebook to submit

        Returns:
            Updated ebook with PENDING status

        Raises:
            ValueError: If ebook not found or not in DRAFT status
        """
        # Retrieve the ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise ValueError(f"Ebook with id {ebook_id} not found")

        # Business rule: only DRAFT ebooks can be submitted for validation
        if ebook.status != EbookStatus.DRAFT:
            raise ValueError(
                f"Cannot submit ebook with status {ebook.status.value}. "
                f"Only DRAFT ebooks can be submitted for validation."
            )

        # Business rule: ebook must have a valid PDF (drive_id and preview_url)
        if not ebook.drive_id or not ebook.preview_url:
            raise ValueError(
                "Cannot submit ebook without a generated PDF. "
                "Please ensure the ebook has been fully generated."
            )

        # Transition to PENDING status
        ebook.status = EbookStatus.PENDING

        # Persist the change
        return await self.ebook_repository.save(ebook)
