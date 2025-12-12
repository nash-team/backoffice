"""Shared validation logic for ebook operations.

This service extracts common validation patterns used across multiple use cases
to eliminate code duplication and ensure consistent error messages.
"""

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode


class EbookValidator:
    """Centralized validation for ebook operations.

    Provides static methods for common validation patterns:
    - Existence validation
    - Status validation (DRAFT, APPROVED, etc.)
    - Structure validation (pages_meta presence)

    All methods raise DomainError with appropriate ErrorCode and actionable hints.
    """

    @staticmethod
    def validate_exists(ebook: Ebook | None, ebook_id: int) -> Ebook:
        """Validate that an ebook exists.

        Args:
            ebook: The ebook instance or None if not found
            ebook_id: The ID that was searched for

        Returns:
            The ebook instance if it exists

        Raises:
            DomainError: If ebook is None (EBOOK_NOT_FOUND)
        """
        if not ebook:
            raise DomainError(
                code=ErrorCode.EBOOK_NOT_FOUND,
                message=f"Ebook {ebook_id} not found",
                actionable_hint="Verify the ebook ID is correct",
            )
        return ebook

    @staticmethod
    def validate_draft_status(ebook: Ebook) -> None:
        """Validate that an ebook is in DRAFT status.

        Args:
            ebook: The ebook to validate

        Raises:
            DomainError: If ebook is not DRAFT (INVALID_STATE)
        """
        if ebook.status != EbookStatus.DRAFT:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Cannot modify ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT ebooks can be modified. Reset to DRAFT first.",
            )

    @staticmethod
    def validate_editable_status(ebook: Ebook) -> None:
        """Validate that an ebook can be edited (DRAFT or APPROVED).

        Args:
            ebook: The ebook to validate

        Raises:
            DomainError: If ebook is not in editable status (INVALID_STATE)
        """
        editable_statuses = {EbookStatus.DRAFT, EbookStatus.APPROVED}
        if ebook.status not in editable_statuses:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Cannot edit ebook with status {ebook.status.value}",
                actionable_hint="Only DRAFT or APPROVED ebooks can be edited",
            )

    @staticmethod
    def validate_structure(ebook: Ebook) -> None:
        """Validate that an ebook has valid structure_json with pages_meta.

        Args:
            ebook: The ebook to validate

        Raises:
            DomainError: If structure_json is missing or invalid (VALIDATION_ERROR)
        """
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook has no structure data",
                actionable_hint="The ebook must be fully generated before this operation",
            )

    @staticmethod
    def validate_page_index(ebook: Ebook, page_index: int, include_back_cover: bool = False) -> None:
        """Validate that a page index is valid for the ebook.

        Args:
            ebook: The ebook to validate against
            page_index: The page index to validate
            include_back_cover: If True, allows index up to last page (back cover)

        Raises:
            DomainError: If page_index is out of bounds (VALIDATION_ERROR)
        """
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook has no structure data",
                actionable_hint="The ebook must be fully generated first",
            )

        pages_meta = ebook.structure_json["pages_meta"]
        max_index = len(pages_meta) - 1 if include_back_cover else len(pages_meta) - 2

        if page_index < 0 or page_index > max_index:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid page index {page_index}. Must be between 0 and {max_index}",
                actionable_hint=f"Valid page indices are 0 to {max_index}",
            )

    @staticmethod
    def validate_for_regeneration(ebook: Ebook | None, ebook_id: int) -> Ebook:
        """Validate ebook for regeneration operations.

        Combines existence, editable status, and structure validation.

        Args:
            ebook: The ebook instance or None
            ebook_id: The ID that was searched for

        Returns:
            The validated ebook instance

        Raises:
            DomainError: If any validation fails
        """
        validated_ebook = EbookValidator.validate_exists(ebook, ebook_id)
        EbookValidator.validate_editable_status(validated_ebook)
        EbookValidator.validate_structure(validated_ebook)
        return validated_ebook

    @staticmethod
    def validate_for_export(ebook: Ebook | None, ebook_id: int) -> Ebook:
        """Validate ebook for export operations.

        Combines existence, APPROVED status, and structure validation.

        Args:
            ebook: The ebook instance or None
            ebook_id: The ID that was searched for

        Returns:
            The validated ebook instance

        Raises:
            DomainError: If any validation fails
        """
        validated_ebook = EbookValidator.validate_exists(ebook, ebook_id)

        if validated_ebook.status != EbookStatus.APPROVED:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Cannot export ebook with status {validated_ebook.status.value}",
                actionable_hint="Only APPROVED ebooks can be exported. Approve the ebook first.",
            )

        EbookValidator.validate_structure(validated_ebook)
        return validated_ebook

    @staticmethod
    def validate_for_approval(ebook: Ebook | None, ebook_id: int) -> Ebook:
        """Validate ebook for approval operations.

        Combines existence, DRAFT status, and structure validation.

        Args:
            ebook: The ebook instance or None
            ebook_id: The ID that was searched for

        Returns:
            The validated ebook instance

        Raises:
            DomainError: If any validation fails
        """
        validated_ebook = EbookValidator.validate_exists(ebook, ebook_id)
        EbookValidator.validate_draft_status(validated_ebook)
        EbookValidator.validate_structure(validated_ebook)
        return validated_ebook
