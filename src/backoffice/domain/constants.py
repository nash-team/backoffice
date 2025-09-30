"""
Configuration constants for the ebook generation system.

This module centralizes all magic numbers, default values, and configuration
constants to improve maintainability and reduce duplication.
"""

from enum import Enum
from typing import NamedTuple, TypedDict

# Default values for ebook generation
DEFAULT_AUTHOR = "Assistant IA"
DEFAULT_TITLE_FALLBACK = "Sans titre"
DEFAULT_EBOOK_FORMAT = "pdf"
DEFAULT_PDF_ENGINE = "weasyprint"

# Slug generation configuration
SLUG_MAX_LENGTH = 64
SLUG_FALLBACK = "ebook"

# Title extraction configuration
TITLE_MAX_WORDS = 6
TITLE_MIN_WORDS = 3

# Cover configuration
COVER_TITLE_MAX_LINES_DEFAULT = 3

# Chapter numbering styles
CHAPTER_NUMBERING_ARABIC = "arabic"
CHAPTER_NUMBERING_ROMAN = "roman"
CHAPTER_NUMBERING_LETTERS = "letters"

# Template paths (relative to templates directory)
COVER_TEMPLATE_PATH = "cover.html"

# Page layout constants
PAGE_SIZE_A4 = "A4"
PAGE_MARGIN_STANDARD = "2cm"
PAGE_MARGIN_MINIMAL = "1cm"
PAGE_MARGIN_NONE = "0"

# PDF generation constants
PDF_FONT_FAMILY_DEFAULT = '"Georgia", "Times New Roman", serif'
PDF_LINE_HEIGHT_DEFAULT = 1.6
PDF_COLOR_DEFAULT = "#333"

# TOC constants
TOC_TITLE_DEFAULT = "Sommaire"
TOC_ID_DEFAULT = "toc"

# Template variants
TEMPLATE_VARIANTS = {
    "cover": ["story", "coloring", "minimal", "classic"],
    "toc": ["standard", "mixed", "detailed"],
    "text": ["chapter", "poem", "story"],
    "image": ["coloring", "illustration", "photo"],
    "chapter_break": ["decorative", "simple"],
    "back_cover": ["simple", "summary"],
}

# File extensions
SUPPORTED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
SUPPORTED_EBOOK_FORMATS = ["pdf", "epub"]

# Content validation
MAX_TITLE_LENGTH = 200
MAX_AUTHOR_LENGTH = 100
MIN_CONTENT_LENGTH = 10

# Ebook configuration validation
MIN_CHAPTERS = 1
MAX_CHAPTERS = 15
MIN_PAGES = 1
MAX_PAGES = 30

# Error messages
ERROR_MSG_TEMPLATE_NOT_FOUND = "Template not found: {template_path}"
ERROR_MSG_INVALID_CONTENT_TYPE = "Content type not supported: {content_type}"
ERROR_MSG_INVALID_VARIANT = (
    "Variant '{variant}' not available for {content_type}. Available variants: {available}"
)
ERROR_MSG_PDF_GENERATION_FAILED = "PDF generation failed: {error}"
ERROR_MSG_TEMPLATE_RENDERING_FAILED = "Template rendering failed: {error}"

# Logging messages
LOG_MSG_TEMPLATE_LOADED = "Template loaded successfully: {template_path}"
LOG_MSG_PDF_GENERATED = "PDF generated successfully: {size} bytes"
LOG_MSG_COVER_GENERATED = "Cover generated successfully. Title: '{title}', Author: '{author}'"
LOG_MSG_USING_DEFAULT_AUTHOR = "No author found, using default: {author}"
LOG_MSG_USING_FALLBACK_TITLE = "No title found, using fallback '{title}'"

# Regular expressions
REGEX_CLEAN_SLUG = r"[^\w\s-]"
REGEX_NORMALIZE_SPACES = r"[-\s]+"
REGEX_SENTENCE_SPLIT = r"[.!?]+"


# Page format constants for different ebook types with KDP compliance
class PageFormat(Enum):
    """Supported page formats for ebook generation."""

    A4 = "A4"
    SQUARE_8_5 = "SQUARE_8_5"


class PageDimensions(NamedTuple):
    """Page dimensions in inches."""

    width: float
    height: float


class PageMargins(NamedTuple):
    """Page margins in inches for print compatibility."""

    outer: float  # Left/right margins
    inner: float  # Top/bottom margins (gutter for binding)


class ImageResolution(NamedTuple):
    """Required image resolution specifications."""

    cover_min_pixels: int  # Minimum pixels for cover images
    content_min_pixels: int  # Minimum pixels for content images
    dpi_requirement: int  # DPI requirement for print quality


class PageSpecification(TypedDict):
    """Type definition for page specification dictionary."""

    dimensions: PageDimensions
    margins: PageMargins
    resolution: ImageResolution


# Page format specifications
PAGE_SPECIFICATIONS: dict[PageFormat, PageSpecification] = {
    PageFormat.A4: {
        "dimensions": PageDimensions(width=8.27, height=11.69),  # A4 in inches
        "margins": PageMargins(outer=0.75, inner=0.75),
        "resolution": ImageResolution(
            cover_min_pixels=2480,  # 300 DPI for 8.27" width
            content_min_pixels=2100,  # Content area consideration
            dpi_requirement=300,
        ),
    },
    PageFormat.SQUARE_8_5: {
        "dimensions": PageDimensions(width=8.5, height=8.5),
        "margins": PageMargins(outer=0.5, inner=0.75),  # KDP compliant
        "resolution": ImageResolution(
            cover_min_pixels=2550,  # 300 DPI for full 8.5" coverage
            content_min_pixels=2175,  # 300 DPI for 7.25" content area
            dpi_requirement=300,
        ),
    },
}


# Content area calculations
def get_content_area_dimensions(page_format: PageFormat) -> PageDimensions:
    """Calculate usable content area after removing margins."""
    spec = PAGE_SPECIFICATIONS[page_format]
    dims: PageDimensions = spec["dimensions"]
    margins: PageMargins = spec["margins"]

    # Content area = total - outer margin - inner margin
    content_width = dims.width - margins.outer - margins.inner
    content_height = dims.height - margins.outer - margins.inner

    return PageDimensions(width=content_width, height=content_height)


# Quick access constants for square format (most used)
SQUARE_8_5_DIMENSIONS = PAGE_SPECIFICATIONS[PageFormat.SQUARE_8_5]["dimensions"]
SQUARE_8_5_MARGINS = PAGE_SPECIFICATIONS[PageFormat.SQUARE_8_5]["margins"]
SQUARE_8_5_RESOLUTION = PAGE_SPECIFICATIONS[PageFormat.SQUARE_8_5]["resolution"]
SQUARE_8_5_CONTENT_AREA = get_content_area_dimensions(PageFormat.SQUARE_8_5)  # 7.25" x 7.25"

# DPI validation constants
MIN_DPI_REQUIREMENT = 300
COVER_MIN_PIXELS_SQUARE = 2550  # For 8.5" at 300 DPI
CONTENT_MIN_PIXELS_SQUARE = 2175  # For 7.25" content area at 300 DPI
