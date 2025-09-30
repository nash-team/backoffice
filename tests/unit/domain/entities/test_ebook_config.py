import pytest

from backoffice.domain.entities.ebook import EbookConfig


class TestEbookConfig:
    """Test cases for EbookConfig entity"""

    def test_default_config_creation(self):
        """Test creating EbookConfig with default values"""
        config = EbookConfig()

        assert config.toc is True
        assert config.cover_enabled is True
        assert config.format == "pdf"
        assert config.number_of_chapters is None
        assert config.number_of_pages is None

    def test_config_with_valid_chapters(self):
        """Test creating EbookConfig with valid number of chapters"""
        config = EbookConfig(number_of_chapters=5)

        assert config.number_of_chapters == 5
        assert config.number_of_pages is None

    def test_config_with_valid_pages(self):
        """Test creating EbookConfig with valid number of pages"""
        config = EbookConfig(number_of_pages=10)

        assert config.number_of_pages == 10
        assert config.number_of_chapters is None

    def test_config_with_both_chapters_and_pages(self):
        """Test creating EbookConfig with both chapters and pages"""
        config = EbookConfig(number_of_chapters=3, number_of_pages=12)

        assert config.number_of_chapters == 3
        assert config.number_of_pages == 12

    def test_invalid_chapters_too_low(self):
        """Test validation for chapters below minimum"""
        with pytest.raises(ValueError, match="Number of chapters must be between 1 and 15"):
            EbookConfig(number_of_chapters=0)

    def test_invalid_chapters_too_high(self):
        """Test validation for chapters above maximum"""
        with pytest.raises(ValueError, match="Number of chapters must be between 1 and 15"):
            EbookConfig(number_of_chapters=16)

    def test_invalid_pages_too_low(self):
        """Test validation for pages below minimum"""
        with pytest.raises(ValueError, match="Number of pages must be between 1 and 30"):
            EbookConfig(number_of_pages=0)

    def test_invalid_pages_too_high(self):
        """Test validation for pages above maximum"""
        with pytest.raises(ValueError, match="Number of pages must be between 1 and 30"):
            EbookConfig(number_of_pages=31)

    def test_invalid_chapters_non_integer(self):
        """Test validation for non-integer chapters"""
        with pytest.raises(ValueError, match="Number of chapters must be an integer, got str"):
            EbookConfig(number_of_chapters="5")

    def test_invalid_pages_non_integer(self):
        """Test validation for non-integer pages"""
        with pytest.raises(ValueError, match="Number of pages must be an integer, got str"):
            EbookConfig(number_of_pages="10")

    def test_valid_boundary_chapters(self):
        """Test valid boundary values for chapters"""
        config_min = EbookConfig(number_of_chapters=1)
        config_max = EbookConfig(number_of_chapters=15)

        assert config_min.number_of_chapters == 1
        assert config_max.number_of_chapters == 15

    def test_valid_boundary_pages(self):
        """Test valid boundary values for pages"""
        config_min = EbookConfig(number_of_pages=1)
        config_max = EbookConfig(number_of_pages=30)

        assert config_min.number_of_pages == 1
        assert config_max.number_of_pages == 30
