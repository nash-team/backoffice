import logging

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.entities.page_content import EbookPages, PageContent
from backoffice.domain.services.page_factory import PageFactory
from backoffice.domain.services.template_registry import create_auto_toc_page

logger = logging.getLogger(__name__)


class EbookStructureConverter:
    """Converts legacy ebook structures to the new modular page format"""

    def __init__(self, page_factory=None):
        self.page_factory = page_factory or PageFactory()

    def convert_structure_to_pages(
        self, ebook_structure: EbookStructure, config: EbookConfig
    ) -> EbookPages:
        """
        Convert a legacy ebook structure to the new modular format

        Args:
            ebook_structure: Legacy ebook structure
            config: Ebook configuration

        Returns:
            Modular page structure
        """
        pages: list[PageContent] = []

        # 1. Add cover if enabled
        if config.cover_enabled:
            cover_page = self.page_factory.create_cover_from_structure(ebook_structure, config)
            pages.append(cover_page)

        # 2. Reserve space for TOC if enabled
        toc_placeholder = None
        if config.toc:
            toc_placeholder = len(pages)

        # 3. Convert sections to text pages
        for i, section in enumerate(ebook_structure.sections or [], 1):
            chapter_page = self.page_factory.create_story_from_section(section, i, config)
            pages.append(chapter_page)

        # 4. Create TOC now that we have all pages
        if toc_placeholder is not None:
            temp_ebook = EbookPages(meta={"title": ebook_structure.meta.title}, pages=pages)
            toc_page = create_auto_toc_page(temp_ebook, variant="standard")
            pages.insert(toc_placeholder, toc_page)

        return EbookPages(
            meta={
                "title": ebook_structure.meta.title,
                "author": ebook_structure.meta.author,
                "engine": "weasyprint",
                "format": config.format,
            },
            pages=pages,
        )
