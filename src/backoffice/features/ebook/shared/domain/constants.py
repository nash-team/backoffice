"""
Configuration constants for the ebook generation system.

Values are now loaded from YAML config files in config/ directory.
This module provides backward compatibility for existing imports.
"""

from enum import Enum

from backoffice.config import ConfigLoader

# Initialize config loader
_config = ConfigLoader()

# Default values for ebook generation (from config/business/limits.yaml)
DEFAULT_EBOOK_FORMAT = _config.get_default_format()
DEFAULT_PDF_ENGINE = _config.get_default_engine()

# Ebook configuration validation (from config/business/limits.yaml)
_page_limits = _config.get_page_limits()
MIN_PAGES = _page_limits["min"]
MAX_PAGES = _page_limits["max"]

# Legacy: chapters no longer used for coloring books
MIN_CHAPTERS = 1
MAX_CHAPTERS = 15


# Page format constants for different ebook types with KDP compliance
class PageFormat(Enum):
    """Supported page formats for ebook generation."""

    A4 = "A4"
    SQUARE_8_5 = "SQUARE_8_5"


# DPI validation constants (from config/business/limits.yaml)
COVER_MIN_PIXELS_SQUARE = _config.get_cover_min_pixels()
CONTENT_MIN_PIXELS_SQUARE = _config.get_content_min_pixels()
