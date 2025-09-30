import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from backoffice.domain.constants import (
    CHAPTER_NUMBERING_ARABIC,
    COVER_TITLE_MAX_LINES_DEFAULT,
    DEFAULT_EBOOK_FORMAT,
    DEFAULT_PDF_ENGINE,
    DEFAULT_TITLE_FALLBACK,
    MAX_CHAPTERS,
    MAX_PAGES,
    MIN_CHAPTERS,
    MIN_PAGES,
    REGEX_CLEAN_SLUG,
    REGEX_NORMALIZE_SPACES,
    REGEX_SENTENCE_SPLIT,
    SLUG_FALLBACK,
    SLUG_MAX_LENGTH,
    TITLE_MAX_WORDS,
    TITLE_MIN_WORDS,
    TOC_TITLE_DEFAULT,
)


class EbookStatus(Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class EbookConfig:
    toc: bool = True
    toc_title: str = TOC_TITLE_DEFAULT
    chapter_numbering: bool = False
    chapter_numbering_style: str = CHAPTER_NUMBERING_ARABIC
    engine: str = DEFAULT_PDF_ENGINE
    format: str = DEFAULT_EBOOK_FORMAT
    cover_enabled: bool = True
    cover_title_override: str | None = None
    cover_title_max_lines: int = COVER_TITLE_MAX_LINES_DEFAULT
    number_of_chapters: int | None = None
    number_of_pages: int | None = None

    # Ribbon configuration for coloring book covers
    ribbon_title: str | None = None
    ribbon_theme: str = "licornes"
    show_ribbon: bool = True

    # LLM Model Selection
    ebook_type: str = "story"  # coloring_book, children_story, professional, story
    image_model: str | None = None  # None = auto-select, or explicit model ID
    text_model: str | None = None  # None = use default from env, or explicit model ID

    def __post_init__(self):
        """Validate config values after initialization"""
        if self.number_of_chapters is not None:
            if not isinstance(self.number_of_chapters, int):
                type_name = type(self.number_of_chapters).__name__
                raise ValueError(f"Number of chapters must be an integer, got {type_name}")
            if not (MIN_CHAPTERS <= self.number_of_chapters <= MAX_CHAPTERS):
                raise ValueError(
                    f"Number of chapters must be between {MIN_CHAPTERS} and {MAX_CHAPTERS}"
                )

        if self.number_of_pages is not None:
            if not isinstance(self.number_of_pages, int):
                type_name = type(self.number_of_pages).__name__
                raise ValueError(f"Number of pages must be an integer, got {type_name}")
            if not (MIN_PAGES <= self.number_of_pages <= MAX_PAGES):
                raise ValueError(f"Number of pages must be between {MIN_PAGES} and {MAX_PAGES}")


def generate_title_slug(title: str, max_length: int = SLUG_MAX_LENGTH) -> str:
    """Generate a file-safe slug from title"""
    if not title or title.isspace():
        return SLUG_FALLBACK

    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(REGEX_CLEAN_SLUG, "", title.lower())
    slug = re.sub(REGEX_NORMALIZE_SPACES, "-", slug)
    slug = slug.strip("-")

    # Truncate to max_length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")

    return slug or SLUG_FALLBACK


def extract_title_from_content(content: str) -> str:
    """Extract a short title from content (3-6 words from first sentence)"""
    if not content or content.isspace():
        return DEFAULT_TITLE_FALLBACK

    # Get first sentence
    sentences = re.split(REGEX_SENTENCE_SPLIT, content.strip())
    if not sentences or not sentences[0].strip():
        return DEFAULT_TITLE_FALLBACK

    first_sentence = sentences[0].strip()
    words = first_sentence.split()[:TITLE_MAX_WORDS]  # Take first 6 words max

    if len(words) >= TITLE_MIN_WORDS:
        # Capitalize first letter of each word
        title = " ".join(word.capitalize() for word in words)
        return title

    return DEFAULT_TITLE_FALLBACK


@dataclass
class Ebook:
    id: int
    title: str
    author: str
    created_at: datetime | None
    status: EbookStatus = EbookStatus.DRAFT
    preview_url: str | None = None
    drive_id: str | None = None  # ID du fichier dans Google Drive
    config: EbookConfig | None = None

    # Theme-based generation metadata
    theme_id: str | None = None
    theme_version: str | None = None
    audience: str | None = None

    # Ebook structure as dict (for regeneration)
    structure_json: dict | None = None
