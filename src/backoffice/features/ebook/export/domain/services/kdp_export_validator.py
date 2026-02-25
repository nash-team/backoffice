"""Shared validation logic for KDP export operations.

This service extracts common validation patterns used across KDP export use cases
(export_to_kdp.py and export_to_kdp_interior.py) to eliminate code duplication.
"""

import logging

from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    EbookStatus,
    KDPExportConfig,
)
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode

logger = logging.getLogger(__name__)


class KdpExportValidator:
    """Centralized validation for KDP export operations.

    Provides static methods for common KDP export validation patterns:
    - Ebook existence validation
    - Status validation (APPROVED for download, DRAFT/APPROVED for preview)
    - Page count validation
    - KDP config adjustment for short books

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
                message=f"Ebook with ID {ebook_id} not found",
                actionable_hint="Verify ebook ID",
            )
        return ebook

    @staticmethod
    def validate_export_status(ebook: Ebook, preview_mode: bool, export_type: str = "KDP") -> None:
        """Validate ebook status for KDP export.

        Args:
            ebook: The ebook to validate
            preview_mode: If True, allows DRAFT ebooks for preview
            export_type: Type of export for error messages (e.g., "KDP", "KDP interior")

        Raises:
            DomainError: If ebook status is invalid for the operation (VALIDATION_ERROR)
        """
        if not preview_mode and ebook.status != EbookStatus.APPROVED:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Ebook must be APPROVED to download {export_type} export (current: {ebook.status.value})",
                actionable_hint=f"Only APPROVED ebooks can be downloaded as {export_type}",
            )

        if preview_mode and ebook.status not in [EbookStatus.DRAFT, EbookStatus.APPROVED]:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Ebook must be DRAFT or APPROVED to preview {export_type} (current: {ebook.status.value})",
                actionable_hint="Only DRAFT or APPROVED ebooks can be previewed",
            )

    @staticmethod
    def validate_page_count(ebook: Ebook) -> None:
        """Validate that ebook has page_count for KDP export.

        Args:
            ebook: The ebook to validate

        Raises:
            DomainError: If page_count is missing (VALIDATION_ERROR)
        """
        if not ebook.page_count:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook must have page_count for KDP export",
                actionable_hint="Regenerate the ebook to populate page_count",
            )

    @staticmethod
    def adjust_config_for_short_books(
        ebook: Ebook,
        kdp_config: KDPExportConfig | None,
    ) -> KDPExportConfig:
        """Adjust KDP config for short books (< 24 pages).

        Premium_color paper type requires 24-828 pages. For shorter books,
        automatically switch to standard_color.

        Args:
            ebook: The ebook with page_count
            kdp_config: Optional KDP config to adjust

        Returns:
            Adjusted KDPExportConfig (or default if None provided)
        """
        if kdp_config is None:
            kdp_config = KDPExportConfig()

        if ebook.page_count and ebook.page_count < 24 and kdp_config.paper_type == "premium_color":
            logger.warning(f"Ebook has {ebook.page_count} pages (< 24), switching from premium_color to standard_color")
            return KDPExportConfig(
                trim_size=kdp_config.trim_size,
                bleed_size=kdp_config.bleed_size,
                paper_type="standard_color",
                include_barcode=kdp_config.include_barcode,
                cover_finish=kdp_config.cover_finish,
                icc_rgb_profile=kdp_config.icc_rgb_profile,
            )

        return kdp_config

    @staticmethod
    def validate_for_export(
        ebook: Ebook | None,
        ebook_id: int,
        preview_mode: bool = False,
        export_type: str = "KDP",
    ) -> Ebook:
        """Validate ebook for KDP export operations.

        Combines existence, status, and page_count validation.

        Args:
            ebook: The ebook instance or None
            ebook_id: The ID that was searched for
            preview_mode: If True, allows DRAFT ebooks
            export_type: Type of export for error messages

        Returns:
            The validated ebook instance

        Raises:
            DomainError: If any validation fails
        """
        validated_ebook = KdpExportValidator.validate_exists(ebook, ebook_id)
        KdpExportValidator.validate_export_status(validated_ebook, preview_mode, export_type)
        KdpExportValidator.validate_page_count(validated_ebook)
        return validated_ebook
