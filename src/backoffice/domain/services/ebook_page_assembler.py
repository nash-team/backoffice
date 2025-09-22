import logging

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.page_content import EbookPages, PageContent
from backoffice.domain.services.page_factory import PageFactory
from backoffice.domain.services.template_registry import create_auto_toc_page

logger = logging.getLogger(__name__)


class EbookPageAssembler:
    """Assembles complete ebooks from various content types"""

    def __init__(self):
        self.page_factory = PageFactory()

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
            author: Author name
            story_chapters: List of story chapters
            coloring_images: List of coloring images
            config: Optional configuration

        Returns:
            Modular ebook structure
        """
        if config is None:
            config = EbookConfig()

        pages: list[PageContent] = []

        # 1. Cover
        if config.cover_enabled:
            cover_page = self.page_factory.create_cover_page(
                title=title,
                author=author,
                template="story",
                subtitle="Histoire et Coloriage",
            )
            pages.append(cover_page)

        # 2. TOC placeholder
        toc_placeholder = None
        if config.toc:
            toc_placeholder = len(pages)

        # 3. Mix story and coloring content
        pages.extend(self._mix_story_and_coloring_content(story_chapters, coloring_images, config))

        # 4. Create TOC
        if toc_placeholder is not None:
            temp_ebook = EbookPages(meta={"title": title}, pages=pages)
            toc_page = create_auto_toc_page(temp_ebook, variant="mixed")
            pages.insert(toc_placeholder, toc_page)

        return EbookPages(
            meta={
                "title": title,
                "author": author,
                "engine": "weasyprint",
                "format": config.format,
                "type": "mixed",
            },
            pages=pages,
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
            author: Author name
            chapters: List of chapters [{"title": str, "content": str}]
            config: Optional configuration

        Returns:
            EbookPages containing all ebook pages
        """
        if config is None:
            config = EbookConfig(cover_enabled=True, toc=True)

        pages: list[PageContent] = []
        toc_placeholder = None

        # 1. Cover page
        if config.cover_enabled:
            cover_page = self.page_factory.create_cover_page(
                title=title, author=author, template="story"
            )
            pages.append(cover_page)

        # 2. TOC placeholder
        if config.toc:
            toc_placeholder = len(pages)

        # 3. Story chapters
        for i, chapter in enumerate(chapters, 1):
            story_page = self.page_factory.create_story_page(
                content_html=chapter["content"],
                title=chapter["title"],
                page_id=f"story-{i}",
                template="story",
                chapter_number=i if config.chapter_numbering else None,
            )
            pages.append(story_page)

        # 4. Create TOC
        if toc_placeholder is not None:
            temp_ebook = EbookPages(meta={"title": title}, pages=pages)
            toc_page = create_auto_toc_page(temp_ebook, variant="story")
            pages.insert(toc_placeholder, toc_page)

        return EbookPages(
            meta={
                "title": title,
                "author": author,
                "engine": "weasyprint",
                "format": config.format,
                "type": "story",
            },
            pages=pages,
        )

    def create_coloring_ebook(
        self,
        title: str,
        author: str,
        images: list[dict],
        config: EbookConfig | None = None,
    ) -> EbookPages:
        """
        Create a pure coloring ebook

        Args:
            title: Ebook title
            author: Author name
            images: List of images [{"url": str, "title": str?, "alt_text": str?}]
            config: Optional configuration

        Returns:
            EbookPages containing all ebook pages
        """
        if config is None:
            config = EbookConfig(cover_enabled=True, toc=True)

        pages: list[PageContent] = []
        toc_placeholder = None

        # 1. Cover page
        if config.cover_enabled:
            cover_page = self.page_factory.create_cover_page(
                title=title, author=author, template="coloring"
            )
            pages.append(cover_page)

        # 2. TOC placeholder
        if config.toc:
            toc_placeholder = len(pages)

        # 3. Coloring images
        for i, image in enumerate(images, 1):
            coloring_page = self.page_factory.create_coloring_page(
                image_url=image["url"],
                page_id=f"coloring-{i}",
                title=image.get("title", f"Coloriage {i}"),
                alt_text=image.get("alt_text", "Image à colorier"),
                display_in_toc=image.get("display_in_toc", True),
            )
            pages.append(coloring_page)

        # 4. Create TOC
        if toc_placeholder is not None:
            temp_ebook = EbookPages(meta={"title": title}, pages=pages)
            toc_page = create_auto_toc_page(temp_ebook, variant="coloring")
            pages.insert(toc_placeholder, toc_page)

        return EbookPages(
            meta={
                "title": title,
                "author": author,
                "engine": "weasyprint",
                "format": config.format,
                "type": "coloring",
            },
            pages=pages,
        )

    def _mix_story_and_coloring_content(
        self,
        story_chapters: list[dict],
        coloring_images: list[dict],
        config: EbookConfig,
    ) -> list[PageContent]:
        """Mix story and coloring content alternately"""
        pages: list[PageContent] = []
        story_iter = iter(story_chapters)
        coloring_iter = iter(coloring_images)
        page_counter = 1

        # Alternate between story and coloring content
        while True:
            # Add story chapter if available
            try:
                chapter = next(story_iter)
                story_page = self.page_factory.create_story_page(
                    content_html=chapter["content"],
                    title=chapter["title"],
                    page_id=f"story-{page_counter}",
                    template="story",
                    chapter_number=page_counter if config.chapter_numbering else None,
                )
                pages.append(story_page)
                page_counter += 1
            except StopIteration:
                pass

            # Add coloring page if available
            try:
                image = next(coloring_iter)
                coloring_page = self.page_factory.create_coloring_page(
                    image_url=image["url"],
                    page_id=f"coloring-{page_counter}",
                    title=image.get("title", f"Coloriage {page_counter}"),
                    alt_text=image.get("alt_text", "Image à colorier"),
                    display_in_toc=image.get("display_in_toc", False),
                )
                pages.append(coloring_page)
                page_counter += 1
            except StopIteration:
                break

        # Add remaining story chapters
        for chapter in story_iter:
            story_page = self.page_factory.create_story_page(
                content_html=chapter["content"],
                title=chapter["title"],
                page_id=f"story-{page_counter}",
                template="story",
                chapter_number=page_counter if config.chapter_numbering else None,
            )
            pages.append(story_page)
            page_counter += 1

        # Add remaining coloring images
        for image in coloring_iter:
            coloring_page = self.page_factory.create_coloring_page(
                image_url=image["url"],
                page_id=f"coloring-{page_counter}",
                title=image.get("title", f"Coloriage {page_counter}"),
                alt_text=image.get("alt_text", "Image à colorier"),
                display_in_toc=image.get("display_in_toc", False),
            )
            pages.append(coloring_page)
            page_counter += 1

        return pages
