import logging
from pathlib import Path

from backoffice.domain.constants import (
    COVER_TEMPLATE_PATH,
    DEFAULT_AUTHOR,
    DEFAULT_TITLE_FALLBACK,
    LOG_MSG_COVER_GENERATED,
    LOG_MSG_USING_DEFAULT_AUTHOR,
    LOG_MSG_USING_FALLBACK_TITLE,
)
from backoffice.domain.entities.ebook import EbookConfig, extract_title_from_content
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.services.template_utils import CommonTemplateLoader, TemplateRenderingError

logger = logging.getLogger(__name__)


class CoverGenerationError(Exception):
    """Exception raised when cover generation fails"""

    pass


class CoverGenerator:
    """Service for generating cover pages for PDF ebooks"""

    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent.parent / "presentation" / "templates"

        self.templates_dir = templates_dir
        self.template_loader = CommonTemplateLoader(templates_dir)
        logger.info(f"CoverGenerator initialized with templates dir: {templates_dir}")

    def generate_cover_title(
        self,
        config: EbookConfig,
        ebook_structure: EbookStructure | None = None,
        meta_title: str | None = None,
        first_chapter_content: str | None = None,
    ) -> str:
        """
        Generate cover title following the algorithm:
        1. If cover.title_override provided → use it
        2. Else if meta.title provided → use it
        3. Else extract from first chapter content
        4. Else fallback to "Sans titre"
        """
        # Step 1: Check for title override
        if config.cover_title_override and config.cover_title_override.strip():
            logger.info(f"Using cover title override: {config.cover_title_override}")
            return config.cover_title_override.strip()

        # Step 2: Check for meta title
        if ebook_structure and ebook_structure.meta.title.strip():
            logger.info(f"Using ebook structure meta title: {ebook_structure.meta.title}")
            return ebook_structure.meta.title.strip()

        if meta_title and meta_title.strip():
            logger.info(f"Using provided meta title: {meta_title}")
            return meta_title.strip()

        # Step 3: Extract from first chapter
        if first_chapter_content:
            try:
                extracted_title = extract_title_from_content(first_chapter_content)
                if extracted_title != DEFAULT_TITLE_FALLBACK:
                    logger.info(f"Extracted title from content: {extracted_title}")
                    return extracted_title
            except Exception as e:
                logger.warning(f"Failed to extract title from content: {e}")

        if ebook_structure and ebook_structure.sections:
            try:
                first_section = ebook_structure.sections[0]
                content = first_section.content if hasattr(first_section, "content") else ""
                if content:
                    extracted_title = extract_title_from_content(content)
                    if extracted_title != DEFAULT_TITLE_FALLBACK:
                        logger.info(f"Extracted title from ebook structure: {extracted_title}")
                        return extracted_title
            except Exception as e:
                logger.warning(f"Failed to extract title from ebook structure: {e}")

        # Step 4: Fallback
        logger.warning(LOG_MSG_USING_FALLBACK_TITLE.format(title=DEFAULT_TITLE_FALLBACK))
        return DEFAULT_TITLE_FALLBACK

    def generate_cover_author(
        self,
        ebook_structure: EbookStructure | None = None,
        meta_author: str | None = None,
    ) -> str:
        """Generate cover author, using DEFAULT_AUTHOR as fallback"""

        # Check ebook structure first
        if ebook_structure and ebook_structure.meta.author.strip():
            logger.info(f"Using ebook structure author: {ebook_structure.meta.author}")
            return ebook_structure.meta.author.strip()

        # Check provided meta author
        if meta_author and meta_author.strip():
            logger.info(f"Using provided meta author: {meta_author}")
            return meta_author.strip()

        # Fallback to default
        logger.info(LOG_MSG_USING_DEFAULT_AUTHOR.format(author=DEFAULT_AUTHOR))
        return DEFAULT_AUTHOR

    def generate_cover_html(
        self,
        title: str,
        author: str,
        config: EbookConfig,
    ) -> str:
        """Generate cover HTML using the template"""
        try:
            context = {
                "title": title,
                "author": author,
                "max_lines": config.cover_title_max_lines,
            }

            html_content = self.template_loader.render_template(COVER_TEMPLATE_PATH, context)

            logger.info(f"Cover HTML generated successfully for title: {title}")
            return html_content

        except TemplateRenderingError as e:
            logger.error(f"Template error generating cover: {e}")
            raise CoverGenerationError(f"Template error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating cover HTML: {e}")
            raise CoverGenerationError(f"Failed to generate cover HTML: {str(e)}") from e

    def generate_cover(
        self,
        config: EbookConfig,
        ebook_structure: EbookStructure | None = None,
        meta_title: str | None = None,
        meta_author: str | None = None,
        first_chapter_content: str | None = None,
    ) -> str:
        """
        Generate complete cover HTML with title and author.
        Returns html_content
        """

        try:
            # Generate title
            title = self.generate_cover_title(
                config, ebook_structure, meta_title, first_chapter_content
            )

            # Generate author
            author = self.generate_cover_author(ebook_structure, meta_author)

            # Generate HTML
            html_content = self.generate_cover_html(title, author, config)

            logger.info(LOG_MSG_COVER_GENERATED.format(title=title, author=author))
            return html_content

        except Exception as e:
            logger.error(f"Failed to generate cover: {e}")
            raise CoverGenerationError(f"Cover generation failed: {str(e)}") from e
