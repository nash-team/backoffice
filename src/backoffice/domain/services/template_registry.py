import logging
from pathlib import Path

from backoffice.domain.constants import TOC_ID_DEFAULT, TOC_TITLE_DEFAULT
from backoffice.domain.entities.page_content import ContentType, EbookPages, PageContent, PageLayout
from backoffice.domain.services.template_utils import CommonTemplateLoader, TemplateRenderingError

logger = logging.getLogger(__name__)


class TemplateRegistryError(Exception):
    """Erreur du système de registry de templates"""

    pass


class TemplateRegistry:
    """Registry sécurisé pour la gestion des templates modulaires"""

    # Registry des templates autorisés avec leurs variants
    TEMPLATE_REGISTRY = {
        ContentType.COVER: {
            "story": "pages/covers/cover_story.html",
            "coloring": "pages/covers/cover_coloring.html",
            "minimal": "pages/covers/cover_minimal.html",
            "classic": "pages/covers/cover_classic.html",
        },
        ContentType.TOC: {
            "standard": "pages/toc/toc_standard.html",
            "mixed": "pages/toc/toc_mixed.html",
            "detailed": "pages/toc/toc_detailed.html",
            "coloring": "pages/toc/toc_coloring.html",
        },
        ContentType.TEXT: {
            "chapter": "pages/text/text_chapter.html",
            "poem": "pages/text/text_poem.html",
            "story": "pages/text/text_story.html",
        },
        ContentType.FULL_PAGE_IMAGE: {
            "coloring": "pages/images/coloring_page.html",
            "illustration": "pages/images/illustration_page.html",
            "photo": "pages/images/photo_page.html",
        },
        ContentType.CHAPTER_BREAK: {
            "decorative": "pages/misc/chapter_break_decorative.html",
            "simple": "pages/misc/chapter_break_simple.html",
        },
        ContentType.BACK_COVER: {
            "simple": "pages/covers/back_cover_simple.html",
            "summary": "pages/covers/back_cover_summary.html",
        },
    }

    def __init__(self, templates_dir: str | Path):
        """Initialise le registry avec le répertoire de templates"""
        self.templates_dir = Path(templates_dir)
        self.template_loader = CommonTemplateLoader(templates_dir)

    def get_template_path(self, content_type: ContentType, variant: str = "default") -> str:
        """
        Récupère le chemin du template pour un type de contenu et variant donnés

        Args:
            content_type: Type de contenu
            variant: Variant du template (défaut: premier disponible)

        Returns:
            Chemin du template

        Raises:
            TemplateRegistryError: Si le type/variant n'existe pas
        """
        if content_type not in self.TEMPLATE_REGISTRY:
            raise TemplateRegistryError(f"Content type non supporté: {content_type}")

        available_variants = self.TEMPLATE_REGISTRY[content_type]

        # Si variant par défaut, prendre le premier disponible
        if variant == "default":
            variant = list(available_variants.keys())[0]

        if variant not in available_variants:
            available = list(available_variants.keys())
            raise TemplateRegistryError(
                f"Variant '{variant}' non disponible pour {content_type}. "
                f"Variants disponibles: {available}"
            )

        return available_variants[variant]

    def render_page(self, page: PageContent) -> str:
        """
        Rend une page avec son template

        Args:
            page: Page à rendre

        Returns:
            HTML rendu

        Raises:
            TemplateRegistryError: Si le template n'existe pas ou erreur de rendu
        """
        try:
            # Valider que le template existe dans le registry
            template_path = self.get_template_path(page.type, page.template)

            # Préparer le contexte avec toutes les données de la page
            context = {
                "page": page.to_dict(),
                **page.data,  # Merge des données spécifiques à la page
            }

            # Utiliser le template loader commun
            return self.template_loader.render_template(template_path, context)

        except TemplateRenderingError as e:
            logger.error(f"Erreur lors du rendu de la page {page.type}/{page.template}: {e}")
            raise TemplateRegistryError(f"Erreur de rendu: {e}") from e
        except Exception as e:
            logger.error(f"Erreur lors du rendu de la page {page.type}/{page.template}: {e}")
            raise TemplateRegistryError(f"Erreur de rendu: {e}") from e

    def render_ebook(self, ebook: EbookPages) -> str:
        """
        Rend un ebook complet en HTML

        Args:
            ebook: Structure de l'ebook à rendre

        Returns:
            HTML complet de l'ebook
        """
        html_parts = []

        for page in ebook.pages:
            try:
                page_html = self.render_page(page)
                html_parts.append(page_html)
                logger.debug(f"Page rendue: {page.type}/{page.template}")

            except TemplateRegistryError as e:
                logger.error(f"Erreur lors du rendu de la page: {e}")
                # Continuer avec les autres pages
                continue

        return "\n<!-- page-separator -->\n".join(html_parts)

    def get_available_variants(self, content_type: ContentType) -> list[str]:
        """Récupère la liste des variants disponibles pour un type de contenu"""
        if content_type not in self.TEMPLATE_REGISTRY:
            return []
        return list(self.TEMPLATE_REGISTRY[content_type].keys())

    def validate_template_exists(self, content_type: ContentType, variant: str) -> bool:
        """Valide qu'un template existe physiquement"""
        try:
            template_path = self.get_template_path(content_type, variant)
            return self.template_loader.template_exists(template_path)
        except TemplateRegistryError:
            return False


def create_auto_toc_page(ebook: EbookPages, variant: str = "standard") -> PageContent:
    """
    Crée automatiquement une page de table des matières basée sur les pages existantes

    Args:
        ebook: Structure de l'ebook
        variant: Variant de template TOC à utiliser

    Returns:
        Page TOC générée automatiquement
    """
    toc_entries = ebook.get_toc_entries()

    return PageContent(
        type=ContentType.TOC,
        template=variant,
        layout=PageLayout.STANDARD,
        data={
            "title": TOC_TITLE_DEFAULT,
            "entries": [
                {
                    "title": entry.title,
                    "anchor": entry.id,
                    "page_number": None,  # Sera calculé par WeasyPrint
                }
                for entry in toc_entries
            ],
        },
        id=TOC_ID_DEFAULT,
        title=TOC_TITLE_DEFAULT,
        display_in_toc=False,  # La TOC ne s'inclut pas elle-même
    )
