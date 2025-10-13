"""
Tests for custom Jinja2 template filters
"""

import pytest

from backoffice.features.ebook.shared.domain.entities.ebook import EbookStatus
from backoffice.features.shared.presentation.routes.templates import (
    EBOOK_STATUS_CONFIG,
    format_ebook_status_class,
    format_ebook_status_label,
)


class TestEbookStatusFilters:
    """Test suite for ebook status template filters."""

    def test_format_ebook_status_label_draft(self):
        # Given
        status = "DRAFT"

        # When
        result = format_ebook_status_label(status)

        # Then
        assert result == "Brouillon"

    def test_format_ebook_status_label_approved(self):
        # Given
        status = "APPROVED"

        # When
        result = format_ebook_status_label(status)

        # Then
        assert result == "Approuvé"

    def test_format_ebook_status_label_unknown(self):
        # Given
        status = "UNKNOWN_STATUS"

        # When
        result = format_ebook_status_label(status)

        # Then
        assert result == "UNKNOWN_STATUS"  # Fallback to original value

    def test_format_ebook_status_class_draft(self):
        # Given
        status = "DRAFT"

        # When
        result = format_ebook_status_class(status)

        # Then
        assert result == "badge-draft"

    def test_format_ebook_status_class_approved(self):
        # Given
        status = "APPROVED"

        # When
        result = format_ebook_status_class(status)

        # Then
        assert result == "badge-approved"

    def test_format_ebook_status_class_unknown(self):
        # Given
        status = "UNKNOWN_STATUS"

        # When
        result = format_ebook_status_class(status)

        # Then
        assert result == "bg-secondary"  # Default fallback

    def test_status_filters_case_sensitive(self):
        # Given
        status_lower = "draft"
        status_upper = "DRAFT"

        # When
        result_lower = format_ebook_status_label(status_lower)
        result_upper = format_ebook_status_label(status_upper)

        # Then
        assert result_lower == "draft"  # No match, returns original
        assert result_upper == "Brouillon"  # Match found

    def test_status_filters_with_none(self):
        # Given
        status = None

        # When
        label_result = format_ebook_status_label(status)
        class_result = format_ebook_status_class(status)

        # Then
        assert label_result is None
        assert class_result == "bg-secondary"

    def test_enum_completeness_all_status_mapped(self):
        """Test that all EbookStatus enum members are mapped in EBOOK_STATUS_CONFIG."""
        # Given
        all_enum_values = {status.value for status in EbookStatus}
        mapped_values = set(EBOOK_STATUS_CONFIG.keys())

        # Then
        missing_mappings = all_enum_values - mapped_values
        assert missing_mappings == set(), (
            f"Missing mappings for EbookStatus values: {missing_mappings}. "
            "Add them to EBOOK_STATUS_CONFIG in templates.py"
        )

        extra_mappings = mapped_values - all_enum_values
        assert extra_mappings == set(), (
            f"Extra mappings found: {extra_mappings}. "
            "Remove unused entries from EBOOK_STATUS_CONFIG"
        )

    @pytest.mark.parametrize("status", list(EbookStatus))
    def test_all_enum_values_have_valid_label(self, status):
        """Test that every EbookStatus enum value has a valid label mapping."""
        # When
        result = format_ebook_status_label(status.value)

        # Then
        assert result is not None
        assert result != status.value  # Should be translated, not raw value
        assert len(result) > 0

    @pytest.mark.parametrize("status", list(EbookStatus))
    def test_all_enum_values_have_valid_css_class(self, status):
        """Test that every EbookStatus enum value has a valid CSS class mapping."""
        # When
        result = format_ebook_status_class(status.value)

        # Then
        assert result is not None
        assert len(result) > 0
        assert result != "bg-secondary"  # Should not fallback to default
        assert result.startswith("badge-") or result.startswith(
            "bg-"
        )  # Should be a valid CSS class
