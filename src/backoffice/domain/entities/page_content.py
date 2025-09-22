from dataclasses import dataclass
from enum import Enum


class ContentType(Enum):
    """Types de contenu pour les pages d'ebook"""

    COVER = "cover"
    TOC = "toc"
    TEXT = "text"
    FULL_PAGE_IMAGE = "full_page_image"
    CHAPTER_BREAK = "chapter_break"
    BACK_COVER = "back_cover"


class PageLayout(Enum):
    """Types de layout pour les pages"""

    STANDARD = "standard"  # Marges normales, header/footer
    FULL_BLEED = "full_bleed"  # Image pleine page sans marge
    COVER = "cover"  # Page de couverture
    MINIMAL = "minimal"  # Marges réduites


@dataclass
class PageContent:
    """Représente une page individuelle dans un ebook avec son type et ses données"""

    # Identification du type de page
    type: ContentType
    template: str
    layout: PageLayout
    data: dict

    # Navigation & Table des matières
    id: str | None = None
    title: str | None = None
    display_in_toc: bool = False

    # Accessibilité & métadonnées
    alt_text: str | None = None
    description: str | None = None

    # Comportement de page
    page_break_before: bool = False
    page_break_after: bool = False

    def to_dict(self) -> dict:
        """Convertit la page en dictionnaire pour le rendu de template"""
        return {
            "type": self.type.value,
            "template": self.template,
            "layout": self.layout.value,
            "data": self.data,
            "id": self.id,
            "title": self.title,
            "display_in_toc": self.display_in_toc,
            "alt_text": self.alt_text,
            "description": self.description,
            "page_break_before": self.page_break_before,
            "page_break_after": self.page_break_after,
        }


@dataclass
class EbookPages:
    """Structure d'un ebook basé sur des pages modulaires"""

    meta: dict  # Métadonnées globales (titre, auteur, etc.)
    pages: list[PageContent]

    def get_toc_entries(self) -> list[PageContent]:
        """Récupère les pages qui doivent apparaître dans la table des matières"""
        return [page for page in self.pages if page.display_in_toc]

    def get_pages_by_type(self, content_type: ContentType) -> list[PageContent]:
        """Récupère toutes les pages d'un type donné"""
        return [page for page in self.pages if page.type == content_type]

    def has_toc(self) -> bool:
        """Vérifie si l'ebook a une table des matières"""
        return any(page.type == ContentType.TOC for page in self.pages)

    def has_cover(self) -> bool:
        """Vérifie si l'ebook a une couverture"""
        return any(page.type == ContentType.COVER for page in self.pages)
