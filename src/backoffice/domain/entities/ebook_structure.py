from dataclasses import dataclass


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
    type: str  # "chapter", "section", "epilogue", etc.
    title: str
    content: str


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

    def __post_init__(self):
        if self.sections is None:
            self.sections = []
