"""Unit tests for ISBN-13 validation in BackCoverConfigModel."""

import pytest

from backoffice.features.ebook.shared.domain.entities.theme_profile import BackCoverConfigModel


def _make_config(**overrides) -> BackCoverConfigModel:
    """Create a BackCoverConfigModel with defaults, overriding specified fields."""
    defaults = {
        "preview_pages": [0, 1],
        "tagline": "Test tagline",
        "description": "Test description",
        "author": "Test Author",
        "publisher": "Test Publisher",
    }
    defaults.update(overrides)
    return BackCoverConfigModel(**defaults)


class TestISBN13Validation:
    """Tests for ISBN-13 validation in BackCoverConfigModel."""

    def test_valid_isbn_13_accepted(self) -> None:
        config = _make_config(isbn="9781234567897")
        assert config.isbn == "9781234567897"

    def test_isbn_with_hyphens_normalized(self) -> None:
        config = _make_config(isbn="978-1-234-56789-7")
        assert config.isbn == "9781234567897"

    def test_isbn_with_spaces_normalized(self) -> None:
        config = _make_config(isbn="978 1 234 56789 7")
        assert config.isbn == "9781234567897"

    def test_isbn_none_accepted(self) -> None:
        config = _make_config()
        assert config.isbn is None

    def test_isbn_wrong_length_rejected(self) -> None:
        with pytest.raises(ValueError, match="13 digits"):
            _make_config(isbn="978123456")

    def test_isbn_too_long_rejected(self) -> None:
        with pytest.raises(ValueError, match="13 digits"):
            _make_config(isbn="97812345678901")

    def test_isbn_invalid_prefix_rejected(self) -> None:
        with pytest.raises(ValueError, match="978 or 979"):
            _make_config(isbn="9771234567898")

    def test_isbn_invalid_check_digit_rejected(self) -> None:
        with pytest.raises(ValueError, match="check digit"):
            _make_config(isbn="9781234567890")

    def test_isbn_non_digits_rejected(self) -> None:
        with pytest.raises(ValueError, match="digits"):
            _make_config(isbn="978123456789X")

    def test_isbn_979_prefix_accepted(self) -> None:
        config = _make_config(isbn="9791095546078")
        assert config.isbn == "9791095546078"
