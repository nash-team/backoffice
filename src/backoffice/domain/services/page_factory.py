import logging

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.entities.page_content import (
    ContentType,
    PageContent,
    PageLayout,
)

logger = logging.getLogger(__name__)


class PageFactory:
    """Factory for creating individual page content objects"""

    @staticmethod
    def create_cover_page(
        title: str,
        author: str,
        template: str = "story",
        subtitle: str | None = None,
        image_url: str | None = None,
    ) -> PageContent:
        """Create a cover page with the given parameters"""
        return PageContent(
            type=ContentType.COVER,
            template=template,
            layout=PageLayout.COVER,
            data={
                "title": title,
                "subtitle": subtitle,
                "author": author,
                "image_url": image_url,
            },
            id="cover",
            title="Couverture",
            display_in_toc=False,
            page_break_after=True,
        )

    @staticmethod
    def create_story_page(
        content_html: str,
        title: str,
        page_id: str,
        template: str = "story",
        chapter_number: int | None = None,
    ) -> PageContent:
        """Create a story/text page with the given content"""
        return PageContent(
            type=ContentType.TEXT,
            template=template,
            layout=PageLayout.STANDARD,
            data={
                "content_html": content_html,
                "chapter_number": chapter_number,
            },
            id=page_id,
            title=title,
            display_in_toc=True,
            page_break_before=True,
        )

    @staticmethod
    def create_coloring_page(
        image_url: str,
        page_id: str,
        title: str | None = None,
        alt_text: str = "Image à colorier",
        display_in_toc: bool = True,
    ) -> PageContent:
        """Create a coloring page with an image"""
        # Check if image_url is a data URL (base64 encoded)
        if image_url and image_url.startswith("data:image/"):
            # Extract base64 data from data URL
            try:
                # Format: data:image/png;base64,<base64_data>
                if "," not in image_url:
                    raise ValueError("Invalid data URL format")

                mime_part, data_part = image_url.split(",", 1)

                # Extract format more efficiently
                mime_type = mime_part.split(";")[0]  # data:image/png
                if "/" not in mime_type:
                    raise ValueError("Invalid MIME type")

                image_format = mime_type.split("/", 1)[1]  # png, jpeg, etc.

                page_data = {
                    "image_data": data_part,  # Just the base64 string without prefix
                    "image_format": image_format,
                    "alt_text": alt_text,
                }
            except (ValueError, IndexError) as e:
                # Fallback if data URL parsing fails
                logger.warning(f"Failed to parse data URL: {e}, using as regular URL")
                page_data = {
                    "image_url": image_url,
                    "alt_text": alt_text,
                }
        else:
            # Regular URL
            page_data = {
                "image_url": image_url,
                "alt_text": alt_text,
            }

        return PageContent(
            type=ContentType.FULL_PAGE_IMAGE,
            template="coloring",
            layout=PageLayout.FULL_BLEED,
            data=page_data,
            id=page_id,
            title=title or "Coloriage",
            display_in_toc=display_in_toc,
            page_break_before=True,
        )

    @classmethod
    def create_cover_from_structure(
        cls, ebook_structure: EbookStructure, config: EbookConfig
    ) -> PageContent:
        """Create a cover page from an ebook structure and config"""
        title = config.cover_title_override or ebook_structure.meta.title
        return cls.create_cover_page(
            title=title,
            author=ebook_structure.meta.author,
            template="story",
        )

    @classmethod
    def create_story_from_section(
        cls,
        section,
        section_index: int,
        config: EbookConfig,
        template: str = "chapter",
    ) -> PageContent:
        """Create a story page from a section"""
        chapter_number = section_index if config.chapter_numbering else None
        return cls.create_story_page(
            content_html=section.content,
            title=section.title,
            page_id=f"chapter-{section_index}",
            template=template,
            chapter_number=chapter_number,
        )
