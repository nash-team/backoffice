from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from backoffice.config import ConfigLoader
from backoffice.features.ebook.shared.domain.constants import (
    DEFAULT_EBOOK_FORMAT,
    DEFAULT_PDF_ENGINE,
    MAX_CHAPTERS,
    MAX_PAGES,
    MIN_CHAPTERS,
    MIN_PAGES,
)

# Initialize config loader for KDP specs
_config = ConfigLoader()


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
    """Configuration for Amazon KDP paperback export.

    All default values and valid options are loaded from config/kdp/specifications.yaml
    This allows modifying KDP specs without touching code.
    """

    trim_size: tuple[float, float] = field(default_factory=lambda: _config.get_kdp_trim_size())
    bleed_size: float = field(default_factory=lambda: _config.get_kdp_bleed())
    paper_type: str = field(default_factory=lambda: _config.get_default_paper_type())
    include_barcode: bool = field(default_factory=lambda: _config.get_default_include_barcode())
    cover_finish: str = field(default_factory=lambda: _config.get_default_cover_finish())
    icc_rgb_profile: str = field(default_factory=lambda: _config.get_color_profiles()["rgb"])
    icc_cmyk_profile: str = field(default_factory=lambda: _config.get_color_profiles()["cmyk"])

    def __post_init__(self):
        """Validate config values against YAML specifications."""
        # Validate paper_type
        valid_papers = _config.get_valid_paper_types()
        if self.paper_type not in valid_papers:
            raise ValueError(
                f"Invalid paper_type: '{self.paper_type}'. "
                f"Must be one of: {', '.join(valid_papers)}. "
                f"Check config/kdp/specifications.yaml"
            )

        # Validate cover_finish
        valid_finishes = _config.get_valid_cover_finishes()
        if self.cover_finish not in valid_finishes:
            raise ValueError(
                f"Invalid cover_finish: '{self.cover_finish}'. "
                f"Must be one of: {', '.join(valid_finishes)}. "
                f"Check config/kdp/specifications.yaml"
            )


# KDP utility functions
def calculate_spine_width(page_count: int, paper_type: str) -> float:
    """Calculate spine width in inches according to KDP formulas.

    Formula loaded from config/kdp/specifications.yaml
    """
    formula = _config.get_spine_formula(paper_type)
    return page_count * formula


# Spine width constants (from config/kdp/specifications.yaml)
MIN_SPINE_WIDTH_FOR_TEXT = _config.get_spine_min_width()
RECOMMENDED_SPINE_WIDTH = _config.get_spine_recommended_width()
MIN_SPINE_MARGIN = _config.get_spine_min_width()  # Same as min width


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
