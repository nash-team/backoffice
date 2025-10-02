from dataclasses import dataclass

from backoffice.domain.entities.image_page import ImagePage


@dataclass
class EbookMeta:
    title: str
    subtitle: str | None = None
    author: str = "Assistant IA"
    language: str = "fr"
    genre: str | None = None
    trim: str = "A4"
    cover_color: str = "#2c3e50"
    engine: str = "weasyprint"


@dataclass
class EbookCover:
    title: str
    subtitle: str | None = None
    tagline: str | None = None
    image_url: str | None = None


@dataclass
class EbookSection:
    type: str  # "chapter", "section", "epilogue", "image_page", etc.
    title: str
    content: str
    image_page: ImagePage | None = None  # For image-based sections


@dataclass
class EbookBackCover:
    blurb: str | None = None
    about_author: str | None = None


@dataclass
class EbookStructure:
    meta: EbookMeta
    cover: EbookCover
    toc: bool = True
    sections: list[EbookSection] | None = None
    back_cover: EbookBackCover | None = None
    image_pages: list[ImagePage] | None = None  # Dedicated image pages

    def __post_init__(self):
        if self.sections is None:
            self.sections = []
        if self.image_pages is None:
            self.image_pages = []

    def add_coloring_page_section(self, image_page: ImagePage) -> None:
        """Add a coloring page as a dedicated section"""
        if self.sections is None:
            self.sections = []

        section = EbookSection(
            type="image_page",
            title=image_page.title,
            content="",  # No text content for image pages
            image_page=image_page,
        )
        self.sections.append(section)
