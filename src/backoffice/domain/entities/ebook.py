from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

from backoffice.domain.constants import (
    DEFAULT_EBOOK_FORMAT,
    DEFAULT_PDF_ENGINE,
    MAX_CHAPTERS,
    MAX_PAGES,
    MIN_CHAPTERS,
    MIN_PAGES,
)


class EbookStatus(Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class EbookConfig:
    engine: str = DEFAULT_PDF_ENGINE
    format: str = DEFAULT_EBOOK_FORMAT
    number_of_chapters: int | None = None
    number_of_pages: int | None = None
    ebook_type: str = "story"  # coloring_book, children_story, professional, story

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


@dataclass
class Ebook:
    id: int | None
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

    # Page count for KDP export
    page_count: int | None = None

    # Note: Generation costs now tracked via generation_costs feature (event-driven)


# KDP Export configurations
@dataclass
class BackCoverConfig:
    """Configuration for Amazon KDP back cover generation."""

    author_name: str
    theme: str
    include_copyright: bool = True
    copyright_year: int | None = None  # Si None → année actuelle


@dataclass
class KDPExportConfig:
    """Configuration for Amazon KDP paperback export."""

    trim_size: tuple[float, float] = (8.0, 10.0)  # pouces (largeur, hauteur)
    bleed_size: float = 0.125  # pouces (obligatoire KDP)
    paper_type: Literal["premium_color", "standard_color", "white", "cream"] = "premium_color"
    include_barcode: bool = True
    cover_finish: Literal["glossy", "matte"] = "glossy"
    icc_rgb_profile: str = "sRGB.icc"
    icc_cmyk_profile: str = "CoatedFOGRA39.icc"  # Europe (ou US Web Coated SWOP v2)


# KDP utility functions
def calculate_spine_width(page_count: int, paper_type: str) -> float:
    """Calculate spine width in inches according to KDP formulas."""
    formulas = {
        "premium_color": 0.002347,
        "standard_color": 0.002252,
        "white": 0.002252,
        "cream": 0.0025,
    }
    return page_count * formulas[paper_type]


MIN_SPINE_WIDTH_FOR_TEXT = 0.0625  # pouces (hard minimum)
RECOMMENDED_SPINE_WIDTH = 0.08  # pouces (recommandé pour lisibilité)
MIN_SPINE_MARGIN = 0.0625  # pouces (marge haut/bas spine)


def can_have_spine_text(page_count: int, paper_type: str) -> tuple[bool, str]:
    """Check if spine is wide enough for text.

    Returns:
        (can_have_text, reason_or_warning)
    """
    spine_width = calculate_spine_width(page_count, paper_type)

    if spine_width < MIN_SPINE_WIDTH_FOR_TEXT:
        return False, f'Tranche trop étroite ({spine_width:.4f}")'

    if spine_width < RECOMMENDED_SPINE_WIDTH:
        return True, f'⚠️ Tranche borderline ({spine_width:.4f}"), lisibilité non garantie'

    return True, ""


def inches_to_px(inches: float, dpi: int = 300) -> int:
    """Convert inches to pixels, rounded to even number."""
    return round(inches * dpi / 2) * 2
