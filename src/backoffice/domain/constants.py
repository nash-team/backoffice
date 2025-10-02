"""
Configuration constants for the ebook generation system.

This module centralizes all magic numbers, default values, and configuration
constants to improve maintainability and reduce duplication.
"""

from enum import Enum

# Default values for ebook generation
DEFAULT_EBOOK_FORMAT = "pdf"
DEFAULT_PDF_ENGINE = "weasyprint"

# Ebook configuration validation
MIN_CHAPTERS = 1
MAX_CHAPTERS = 15
MIN_PAGES = 24  # Amazon KDP minimum for paperback printing
MAX_PAGES = 30


# Page format constants for different ebook types with KDP compliance
class PageFormat(Enum):
    """Supported page formats for ebook generation."""

    A4 = "A4"
    SQUARE_8_5 = "SQUARE_8_5"


# DPI validation constants (used by OpenRouterImageAdapter)
COVER_MIN_PIXELS_SQUARE = 2550  # For 8.5" at 300 DPI
CONTENT_MIN_PIXELS_SQUARE = 2175  # For 7.25" content area at 300 DPI
