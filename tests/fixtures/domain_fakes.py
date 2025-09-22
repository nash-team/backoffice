"""
Domain-focused fakes that respect only port contracts.
No coupling to implementation details.
"""

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import (
    EbookCover,
    EbookMeta,
    EbookSection,
    EbookStructure,
)
from backoffice.domain.entities.page_content import (
    ContentType,
    EbookPages,
    PageContent,
    PageLayout,
)
from backoffice.domain.ports.content_generation_port import ContentGenerationPort
from backoffice.domain.ports.ebook_generator_port import EbookGeneratorPort
from backoffice.domain.ports.file_storage_port import FileStoragePort


class FakeContentGenerator(ContentGenerationPort):
    """Pure fake respecting ContentGenerationPort contract only."""

    def __init__(self, available: bool = True, should_fail: bool = False):
        self._available = available
        self._should_fail = should_fail

    def is_available(self) -> bool:
        return self._available

    async def generate_ebook_structure(self, prompt: str) -> EbookStructure:
        if self._should_fail:
            raise Exception("Content generation failed")

        # Extract first 3 words for realistic title
        words = prompt.split()[:3]
        title = f"Guide: {' '.join(words).title()}"

        return EbookStructure(
            meta=EbookMeta(title=title, author="Fake Author"),
            cover=EbookCover(title=title),
            sections=[
                EbookSection(type="chapter", title="Chapter 1", content="Fake content 1"),
                EbookSection(type="chapter", title="Chapter 2", content="Fake content 2"),
            ],
        )

    async def generate_ebook_content_legacy(self, prompt: str) -> dict[str, str]:
        if self._should_fail:
            raise Exception("Content generation failed")

        words = prompt.split()[:3]
        title = f"Legacy: {' '.join(words).title()}"

        return {
            "title": title,
            "content": "Legacy fake content",
            "author": "Fake Author",
        }


class FakeEbookGenerator(EbookGeneratorPort):
    """Pure fake respecting EbookGeneratorPort contract only."""

    def __init__(self, supported_formats: list[str] = None, should_fail: bool = False):
        self._supported_formats = supported_formats or ["pdf"]
        self._should_fail = should_fail

    def supports_format(self, format_type: str) -> bool:
        return format_type.lower() in self._supported_formats

    def get_supported_formats(self) -> list[str]:
        return self._supported_formats.copy()

    async def generate_ebook(self, ebook_structure: EbookStructure, config: EbookConfig) -> bytes:
        if self._should_fail:
            raise Exception("Ebook generation failed")

        if not self.supports_format(config.format):
            raise Exception(f"Unsupported format: {config.format}")

        # Realistic fake content based on inputs
        content = f"FAKE {config.format.upper()} - {ebook_structure.meta.title}"
        return content.encode()


class FakeFileStorage(FileStoragePort):
    """Pure fake respecting FileStoragePort contract only."""

    def __init__(self, available: bool = True, should_fail: bool = False):
        self._available = available
        self._should_fail = should_fail
        self._files = {}  # file_id -> file_info

    def is_available(self) -> bool:
        return self._available

    @property
    def uploaded_files(self):
        return list(self._files.values())

    async def upload_ebook(
        self, file_bytes: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> dict[str, str]:
        if self._should_fail:
            raise Exception("Upload failed")

        file_id = f"fake-id-{len(self._files)}"
        file_info = {
            "id": file_id,
            "url": f"https://fake-storage.com/{filename}",
            "filename": filename,
            "size": str(len(file_bytes)),
            "status": "uploaded",
        }

        self._files[file_id] = file_info
        return file_info

    async def get_file_info(self, file_id: str) -> dict[str, str]:
        if self._should_fail:
            raise Exception("Failed to get file info")

        return self._files.get(file_id, {"id": file_id, "status": "not_found"})


# Factory functions for common test scenarios
def create_working_content_generator() -> FakeContentGenerator:
    """Creates a content generator that works normally."""
    return FakeContentGenerator(available=True, should_fail=False)


def create_failing_content_generator() -> FakeContentGenerator:
    """Creates a content generator that fails."""
    return FakeContentGenerator(available=True, should_fail=True)


def create_unavailable_content_generator() -> FakeContentGenerator:
    """Creates an unavailable content generator."""
    return FakeContentGenerator(available=False, should_fail=False)


def create_working_ebook_generator() -> FakeEbookGenerator:
    """Creates an ebook generator that supports PDF."""
    return FakeEbookGenerator(supported_formats=["pdf"], should_fail=False)


def create_failing_ebook_generator() -> FakeEbookGenerator:
    """Creates an ebook generator that fails."""
    return FakeEbookGenerator(supported_formats=["pdf"], should_fail=True)


def create_multi_format_ebook_generator() -> FakeEbookGenerator:
    """Creates an ebook generator that supports multiple formats."""
    return FakeEbookGenerator(supported_formats=["pdf", "epub", "mobi"], should_fail=False)


def create_working_file_storage() -> FakeFileStorage:
    """Creates a file storage that works normally."""
    return FakeFileStorage(available=True, should_fail=False)


def create_failing_file_storage() -> FakeFileStorage:
    """Creates a file storage that fails."""
    return FakeFileStorage(available=True, should_fail=True)


def create_unavailable_file_storage() -> FakeFileStorage:
    """Creates an unavailable file storage."""
    return FakeFileStorage(available=False, should_fail=False)


# Fakes for modular page generation services
class FakePageFactory:
    """Fake implementation of PageFactory for testing"""

    def __init__(self):
        self.created_pages = []

    def create_cover_page(
        self,
        title: str,
        author: str,
        template: str = "story",
        subtitle: str | None = None,
        image_url: str | None = None,
    ) -> PageContent:
        page = PageContent(
            type=ContentType.COVER,
            template=template,
            layout=PageLayout.COVER,
            data={"title": title, "author": author, "subtitle": subtitle, "image_url": image_url},
            id="cover",
            title="Couverture",
            display_in_toc=False,
            page_break_after=True,
        )
        self.created_pages.append(page)
        return page

    def create_story_page(
        self,
        content_html: str,
        title: str,
        page_id: str,
        template: str = "story",
        chapter_number: int | None = None,
    ) -> PageContent:
        page = PageContent(
            type=ContentType.TEXT,
            template=template,
            layout=PageLayout.STANDARD,
            data={"content_html": content_html, "chapter_number": chapter_number},
            id=page_id,
            title=title,
            display_in_toc=True,
            page_break_before=True,
        )
        self.created_pages.append(page)
        return page

    def create_coloring_page(
        self,
        image_url: str,
        page_id: str,
        title: str | None = None,
        alt_text: str = "Image à colorier",
        display_in_toc: bool = True,
    ) -> PageContent:
        page = PageContent(
            type=ContentType.FULL_PAGE_IMAGE,
            template="coloring",
            layout=PageLayout.FULL_BLEED,
            data={"image_url": image_url, "alt_text": alt_text},
            id=page_id,
            title=title or "Coloriage",
            display_in_toc=display_in_toc,
            page_break_before=True,
        )
        self.created_pages.append(page)
        return page

    def create_cover_from_structure(
        self, ebook_structure: EbookStructure, config: EbookConfig
    ) -> PageContent:
        title = config.cover_title_override or ebook_structure.meta.title
        return self.create_cover_page(title=title, author=ebook_structure.meta.author)

    def create_story_from_section(
        self, section, section_index: int, config: EbookConfig, template: str = "chapter"
    ) -> PageContent:
        chapter_number = section_index if config.chapter_numbering else None
        return self.create_story_page(
            content_html=section.content,
            title=section.title,
            page_id=f"chapter-{section_index}",
            template=template,
            chapter_number=chapter_number,
        )


class FakeTemplateLoader:
    """Fake implementation of CommonTemplateLoader for testing"""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.rendered_templates = []

    def render_template(self, template_path: str, context: dict) -> str:
        if self.should_fail:
            raise Exception(f"Template rendering failed for {template_path}")

        rendered_content = f"FAKE_TEMPLATE:{template_path}:{context.get('title', 'NO_TITLE')}"
        self.rendered_templates.append({"path": template_path, "context": context})
        return rendered_content

    def template_exists(self, template_path: str) -> bool:
        return not self.should_fail


class FakeTemplateRegistry:
    """Fake implementation of TemplateRegistry for testing"""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.rendered_pages = []

    def render_ebook(self, ebook: EbookPages) -> str:
        if self.should_fail:
            raise Exception("Template registry rendering failed")

        rendered_parts = []
        for page in ebook.pages:
            page_html = f"<div class='page {page.type.value}'>{page.title}</div>"
            rendered_parts.append(page_html)
            self.rendered_pages.append(page)

        return "\n".join(rendered_parts)


def create_auto_toc_page_fake(ebook: EbookPages, variant: str = "standard") -> PageContent:
    """Fake implementation of create_auto_toc_page function"""
    toc_entries = ebook.get_toc_entries()
    return PageContent(
        type=ContentType.TOC,
        template=variant,
        layout=PageLayout.STANDARD,
        data={
            "title": "Sommaire",
            "entries": [{"title": entry.title, "anchor": entry.id} for entry in toc_entries],
        },
        id="toc",
        title="Sommaire",
        display_in_toc=False,
    )
