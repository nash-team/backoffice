"""
Configuration constants for the ebook generation system.

This module centralizes all magic numbers, default values, and configuration
constants to improve maintainability and reduce duplication.
"""

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
