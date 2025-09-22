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
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"


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
    status: EbookStatus = EbookStatus.PENDING
    preview_url: str | None = None
    drive_id: str | None = None  # ID du fichier dans Google Drive
    config: EbookConfig | None = None
