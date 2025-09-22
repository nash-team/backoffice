from dataclasses import dataclass
from enum import Enum

from backoffice.domain.entities.ebook import EbookConfig


class EbookType(Enum):
    """Types d'ebooks supportés"""

    STORY = "story"  # Histoire classique
    COLORING = "coloring"  # Livre de coloriage
    MIXED = "mixed"  # Mixte histoire + coloriage


@dataclass
class TemplateTheme:
    """Définit un thème complet avec tous les templates associés"""

    name: str
    display_name: str
    description: str
    cover_template: str
    toc_template: str
    text_template: str
    image_template: str
    compatible_types: list[EbookType]

    def to_dict(self) -> dict:
        """Convertit le thème en dictionnaire pour l'API"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "cover_template": self.cover_template,
            "toc_template": self.toc_template,
            "text_template": self.text_template,
            "image_template": self.image_template,
            "compatible_types": [t.value for t in self.compatible_types],
        }


@dataclass
class ExtendedEbookConfig(EbookConfig):
    """Configuration d'ebook étendue avec support des thèmes modulaires"""

    # Sélection du type d'ebook
    ebook_type: EbookType = EbookType.STORY

    # Templates spécifiques (si différents du thème)
    cover_template: str | None = None
    toc_template: str | None = None
    text_template: str | None = None
    image_template: str | None = None

    # Configuration de thème prédéfini
    theme_name: str | None = None

    def get_effective_templates(self, theme: TemplateTheme | None = None) -> dict[str, str]:
        """
        Récupère les templates effectifs en combinant thème et overrides

        Args:
            theme: Thème prédéfini optionnel

        Returns:
            Dictionnaire des templates à utiliser
        """
        # Templates par défaut basés sur le type d'ebook
        defaults = self._get_default_templates()

        # Templates du thème si spécifié
        if theme:
            defaults.update(
                {
                    "cover": theme.cover_template,
                    "toc": theme.toc_template,
                    "text": theme.text_template,
                    "image": theme.image_template,
                }
            )

        # Overrides spécifiques
        if self.cover_template:
            defaults["cover"] = self.cover_template
        if self.toc_template:
            defaults["toc"] = self.toc_template
        if self.text_template:
            defaults["text"] = self.text_template
        if self.image_template:
            defaults["image"] = self.image_template

        return defaults

    def _get_default_templates(self) -> dict[str, str]:
        """Récupère les templates par défaut selon le type d'ebook"""
        match self.ebook_type:
            case EbookType.STORY:
                return {
                    "cover": "story",
                    "toc": "standard",
                    "text": "chapter",
                    "image": "illustration",
                }
            case EbookType.COLORING:
                return {
                    "cover": "coloring",
                    "toc": "mixed",
                    "text": "story",
                    "image": "coloring",
                }
            case EbookType.MIXED:
                return {
                    "cover": "story",
                    "toc": "mixed",
                    "text": "story",
                    "image": "coloring",
                }
            case _:
                return {
                    "cover": "story",
                    "toc": "standard",
                    "text": "chapter",
                    "image": "illustration",
                }


# Thèmes prédéfinis disponibles
PREDEFINED_THEMES = {
    "classic_story": TemplateTheme(
        name="classic_story",
        display_name="Histoire Classique",
        description="Thème traditionnel pour les histoires avec chapitres",
        cover_template="story",
        toc_template="standard",
        text_template="chapter",
        image_template="illustration",
        compatible_types=[EbookType.STORY],
    ),
    "coloring_fun": TemplateTheme(
        name="coloring_fun",
        display_name="Coloriage Amusant",
        description="Thème optimisé pour les livres de coloriage",
        cover_template="coloring",
        toc_template="mixed",
        text_template="story",
        image_template="coloring",
        compatible_types=[EbookType.COLORING, EbookType.MIXED],
    ),
    "mixed_adventure": TemplateTheme(
        name="mixed_adventure",
        display_name="Aventure Mixte",
        description="Combine histoire et activités de coloriage",
        cover_template="story",
        toc_template="mixed",
        text_template="story",
        image_template="coloring",
        compatible_types=[EbookType.MIXED],
    ),
    "minimal_clean": TemplateTheme(
        name="minimal_clean",
        display_name="Design Minimal",
        description="Design épuré et moderne",
        cover_template="minimal",
        toc_template="standard",
        text_template="chapter",
        image_template="illustration",
        compatible_types=[EbookType.STORY],
    ),
}


def get_compatible_themes(ebook_type: EbookType) -> list[TemplateTheme]:
    """Récupère les thèmes compatibles avec un type d'ebook donné"""
    return [theme for theme in PREDEFINED_THEMES.values() if ebook_type in theme.compatible_types]


def get_theme_by_name(theme_name: str) -> TemplateTheme | None:
    """Récupère un thème par son nom"""
    return PREDEFINED_THEMES.get(theme_name)
