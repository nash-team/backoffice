import logging
from pathlib import Path

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.entities.page_content import ContentType
from backoffice.domain.ports.ebook_generator_port import EbookGeneratorPort
from backoffice.domain.services.modular_page_generator import ModularPageGenerator

logger = logging.getLogger(__name__)


class ModularPDFGeneratorError(Exception):
    """Erreur du générateur PDF modulaire"""

    pass


class ModularPDFGeneratorAdapter(EbookGeneratorPort):
    """Adaptateur PDF utilisant le nouveau système modulaire de pages"""

    def __init__(self):
        """Initialise l'adaptateur avec le générateur modulaire"""
        # Chemin vers les nouveaux templates modulaires
        self.templates_dir = Path(__file__).parent.parent.parent / "presentation" / "templates"
        self.page_generator = ModularPageGenerator(self.templates_dir)
        # self.validation_service = ValidationService()

        logger.info("ModularPDFGeneratorAdapter initialisé avec templates modulaires")

    def supports_format(self, format_name: str) -> bool:
        """Vérifie si le format est supporté"""
        return format_name.lower() == "pdf"

    async def generate_ebook(self, ebook_structure: EbookStructure, config: EbookConfig) -> bytes:
        """
        Génère un PDF à partir d'une structure d'ebook en utilisant le système modulaire

        Args:
            ebook_structure: Structure de l'ebook à générer
            config: Configuration de génération

        Returns:
            PDF bytes
        """
        try:
            logger.info(
                f"Génération PDF modulaire pour '{ebook_structure.meta.title}' "
                f"par {ebook_structure.meta.author}"
            )

            # Convertir la structure classique vers le format modulaire
            ebook_pages = self.page_generator.convert_structure_to_pages(ebook_structure, config)

            # Valider la structure des pages

            # Générer le PDF
            pdf_bytes = self.page_generator.generate_pdf_from_pages(ebook_pages)
            if not isinstance(pdf_bytes, bytes):
                raise ModularPDFGeneratorError(
                    "PDF generation failed: expected bytes, got different type"
                )

            logger.info(f"PDF modulaire généré avec succès: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Erreur lors de la génération PDF modulaire: {e}")
            raise ModularPDFGeneratorError(f"Échec de la génération PDF: {e}") from e

    async def generate_story_ebook(
        self,
        title: str,
        author: str,
        story_chapters: list[dict],
        config: EbookConfig | None = None,
    ) -> bytes:
        """
        Génère un ebook d'histoire pure

        Args:
            title: Titre de l'ebook
            author: Auteur
            story_chapters: Chapitres d'histoire [{"title": str, "content": str}]
            config: Configuration optionnelle

        Returns:
            PDF bytes
        """
        try:
            if config is None:
                config = EbookConfig(cover_enabled=True, toc=True)

            logger.info(f"Génération ebook histoire '{title}' avec {len(story_chapters)} chapitres")

            # Créer la structure histoire pure
            story_ebook = self.page_generator.create_story_ebook(
                title=title, author=author, chapters=story_chapters
            )

            # Générer le PDF
            pdf_bytes = self.page_generator.generate_pdf_from_pages(story_ebook)
            if not isinstance(pdf_bytes, bytes):
                raise ModularPDFGeneratorError(
                    "PDF generation failed: expected bytes, got different type"
                )
            return pdf_bytes

        except Exception as e:
            logger.error(f"Erreur lors de la génération ebook histoire: {e}")
            raise ModularPDFGeneratorError(f"Échec de la génération ebook histoire: {e}") from e

    async def generate_coloring_ebook(
        self,
        title: str,
        author: str,
        coloring_images: list[dict],
        config: EbookConfig | None = None,
    ) -> bytes:
        """
        Génère un ebook de coloriage pur

        Args:
            title: Titre de l'ebook
            author: Auteur
            coloring_images: Images de coloriage [{"url": str, "title": str?, "alt_text": str?}]
            config: Configuration optionnelle

        Returns:
            PDF bytes
        """
        try:
            if config is None:
                config = EbookConfig(cover_enabled=True, toc=True)

            logger.info(f"Génération ebook coloriage '{title}' avec {len(coloring_images)} images")

            # Créer la structure coloriage pure
            coloring_ebook = self.page_generator.create_coloring_ebook(
                title=title, author=author, images=coloring_images
            )

            # Générer le PDF
            pdf_bytes = self.page_generator.generate_pdf_from_pages(coloring_ebook)
            if not isinstance(pdf_bytes, bytes):
                raise ModularPDFGeneratorError(
                    "PDF generation failed: expected bytes, got different type"
                )
            return pdf_bytes

        except Exception as e:
            logger.error(f"Erreur lors de la génération ebook coloriage: {e}")
            raise ModularPDFGeneratorError(f"Échec de la génération ebook coloriage: {e}") from e

    async def generate_mixed_ebook(
        self,
        title: str,
        author: str,
        story_chapters: list[dict],
        coloring_images: list[dict],
        config: EbookConfig | None = None,
    ) -> bytes:
        """
        Génère un ebook mixte histoire + coloriage

        Args:
            title: Titre de l'ebook
            author: Auteur
            story_chapters: Chapitres d'histoire [{"title": str, "content": str}]
            coloring_images: Images de coloriage [{"url": str, "title": str?, "alt_text": str?}]
            config: Configuration optionnelle

        Returns:
            PDF bytes
        """
        try:
            if config is None:
                config = EbookConfig(cover_enabled=True, toc=True)

            logger.info(
                f"Génération ebook mixte '{title}' avec {len(story_chapters)} chapitres "
                f"et {len(coloring_images)} coloriages"
            )

            # Créer la structure mixte
            ebook_pages = self.page_generator.create_mixed_ebook(
                title=title,
                author=author,
                story_chapters=story_chapters,
                coloring_images=coloring_images,
                config=config,
            )

            # Valider la structure

            # Générer le PDF
            pdf_bytes = self.page_generator.generate_pdf_from_pages(ebook_pages)
            if not isinstance(pdf_bytes, bytes):
                raise ModularPDFGeneratorError(
                    "PDF generation failed: expected bytes, got different type"
                )

            logger.info(f"Ebook mixte généré avec succès: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Erreur lors de la génération ebook mixte: {e}")
            raise ModularPDFGeneratorError(f"Échec de la génération ebook mixte: {e}") from e

    def get_supported_formats(self) -> list[str]:
        """Retourne les formats supportés"""
        return ["pdf"]

    def get_available_templates(self) -> dict[str, list[str]]:
        """Retourne les templates disponibles par type de contenu"""
        result = {}
        for content_type in ContentType:
            variants = self.page_generator.template_registry.get_available_variants(content_type)
            if variants:
                result[content_type.value] = variants
        return result
