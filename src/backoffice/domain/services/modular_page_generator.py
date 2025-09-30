import logging
from pathlib import Path

from backoffice.domain.constants import PageFormat
from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.entities.page_content import EbookPages
from backoffice.domain.services.ebook_page_assembler import EbookPageAssembler
from backoffice.domain.services.ebook_structure_converter import EbookStructureConverter
from backoffice.domain.services.pdf_renderer import PdfRenderer

logger = logging.getLogger(__name__)


class ModularPageGeneratorError(Exception):
    """Error from the modular page generator"""

    pass


class ModularPageGenerator:
    """Modular page generator for ebooks with mixed story/coloring support"""

    def __init__(self, templates_dir: str | Path):
        """Initialize the generator with templates directory"""
        self.templates_dir = Path(templates_dir)
        self.converter = EbookStructureConverter()
        self.assembler = EbookPageAssembler()
        self.pdf_renderer = PdfRenderer(templates_dir)

    def convert_structure_to_pages(
        self, ebook_structure: EbookStructure, config: EbookConfig
    ) -> EbookPages:
        """
        Convert a legacy ebook structure to the new modular format

        Args:
            ebook_structure: Existing ebook structure
            config: Ebook configuration

        Returns:
            Modular page structure
        """
        return self.converter.convert_structure_to_pages(ebook_structure, config)

    def create_mixed_ebook(
        self,
        title: str,
        author: str,
        story_chapters: list[dict],
        coloring_images: list[dict],
        config: EbookConfig | None = None,
    ) -> EbookPages:
        """
        Create a mixed story + coloring ebook

        Args:
            title: Ebook title
            author: Author
            story_chapters: List of story chapters
            coloring_images: List of coloring images
            config: Optional configuration

        Returns:
            Modular ebook structure
        """
        return self.assembler.create_mixed_ebook(
            title, author, story_chapters, coloring_images, config
        )

    def create_story_ebook(
        self,
        title: str,
        author: str,
        chapters: list[dict],
        config: EbookConfig | None = None,
    ) -> EbookPages:
        """
        Create a pure story ebook

        Args:
            title: Ebook title
            author: Author
            chapters: List of chapters [{"title": str, "content": str}]
            config: Optional configuration

        Returns:
            EbookPages containing all ebook pages
        """
        return self.assembler.create_story_ebook(title, author, chapters, config)

    def create_coloring_ebook(
        self,
        title: str,
        author: str,
        images: list[dict],
        config: EbookConfig | None = None,
        cover_image_url: str | None = None,
    ) -> EbookPages:
        """
        Create a pure coloring ebook

        Args:
            title: Ebook title
            author: Author
            images: List of images [{"url": str, "title": str?, "alt_text": str?}]
            config: Optional configuration

        Returns:
            EbookPages containing all ebook pages
        """
        return self.assembler.create_coloring_ebook(title, author, images, config, cover_image_url)

    def generate_pdf_from_pages(
        self, ebook: EbookPages, page_format: PageFormat = PageFormat.A4
    ) -> bytes:
        """
        Generate PDF from modular page structure

        Args:
            ebook: Modular ebook structure
            page_format: Page format to use for PDF generation

        Returns:
            PDF bytes
        """
        return self.pdf_renderer.generate_pdf_from_pages(ebook, page_format)
