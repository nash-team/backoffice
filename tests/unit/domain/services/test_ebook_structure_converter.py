from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import (
    EbookCover,
    EbookMeta,
    EbookSection,
    EbookStructure,
)
from backoffice.domain.entities.page_content import ContentType, EbookPages
from backoffice.domain.services.ebook_structure_converter import EbookStructureConverter
from tests.fixtures.domain_fakes import FakePageFactory


class TestEbookStructureConverter:
    """Test suite for EbookStructureConverter using London methodology"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fake_page_factory = FakePageFactory()
        self.converter = EbookStructureConverter(page_factory=self.fake_page_factory)

    def test_convert_structure_without_cover_and_toc(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        section = EbookSection(type="chapter", title="Chapter 1", content="Content 1")
        structure = EbookStructure(meta=meta, cover=cover, sections=[section])
        config = EbookConfig(cover_enabled=False, toc=False)

        # When
        result = self.converter.convert_structure_to_pages(structure, config)

        # Then
        assert isinstance(result, EbookPages)
        assert len(result.pages) == 1
        assert result.pages[0].type == ContentType.TEXT
        assert result.pages[0].title == "Chapter 1"
        assert result.meta["title"] == "Test Title"
        assert result.meta["author"] == "Test Author"
        # Verify no TOC was created since toc=False
        assert all(page.type != ContentType.TOC for page in result.pages)

    def test_convert_structure_with_cover_only(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        section = EbookSection(type="chapter", title="Chapter 1", content="Content 1")
        structure = EbookStructure(meta=meta, cover=cover, sections=[section])
        config = EbookConfig(cover_enabled=True, toc=False)

        # When
        result = self.converter.convert_structure_to_pages(structure, config)

        # Then
        assert len(result.pages) == 2
        assert result.pages[0].type == ContentType.COVER
        assert result.pages[1].type == ContentType.TEXT
        # Verify no TOC was created since toc=False
        assert all(page.type != ContentType.TOC for page in result.pages)

    def test_convert_structure_with_toc_only(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        section = EbookSection(type="chapter", title="Chapter 1", content="Content 1")
        structure = EbookStructure(meta=meta, cover=cover, sections=[section])
        config = EbookConfig(cover_enabled=False, toc=True)

        # When
        result = self.converter.convert_structure_to_pages(structure, config)

        # Then
        assert len(result.pages) == 2
        assert result.pages[0].type == ContentType.TOC  # TOC inserted at position 0
        assert result.pages[1].type == ContentType.TEXT
        # Verify TOC page content
        toc_page = result.pages[0]
        assert toc_page.title == "Sommaire"
        assert toc_page.id == "toc"

    def test_convert_structure_with_cover_and_toc(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        section = EbookSection(type="chapter", title="Chapter 1", content="Content 1")
        structure = EbookStructure(meta=meta, cover=cover, sections=[section])
        config = EbookConfig(cover_enabled=True, toc=True)

        # When
        result = self.converter.convert_structure_to_pages(structure, config)

        # Then
        assert len(result.pages) == 3
        assert result.pages[0].type == ContentType.COVER
        assert result.pages[1].type == ContentType.TOC  # TOC inserted at position 1
        assert result.pages[2].type == ContentType.TEXT
        # Verify TOC page content
        toc_page = result.pages[1]
        assert toc_page.title == "Sommaire"
        assert toc_page.id == "toc"

    def test_convert_structure_with_multiple_sections(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        section1 = EbookSection(type="chapter", title="Chapter 1", content="Content 1")
        section2 = EbookSection(type="chapter", title="Chapter 2", content="Content 2")
        section3 = EbookSection(type="chapter", title="Chapter 3", content="Content 3")
        structure = EbookStructure(meta=meta, cover=cover, sections=[section1, section2, section3])
        config = EbookConfig(cover_enabled=False, toc=False)

        # When
        result = self.converter.convert_structure_to_pages(structure, config)

        # Then
        assert len(result.pages) == 3
        assert all(page.type == ContentType.TEXT for page in result.pages)
        assert result.pages[0].title == "Chapter 1"
        assert result.pages[1].title == "Chapter 2"
        assert result.pages[2].title == "Chapter 3"

    def test_convert_structure_with_empty_sections(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        structure = EbookStructure(meta=meta, cover=cover, sections=[])
        config = EbookConfig(cover_enabled=True, toc=True)

        # When
        result = self.converter.convert_structure_to_pages(structure, config)

        # Then
        assert len(result.pages) == 2  # Only cover + TOC
        assert result.pages[0].type == ContentType.COVER
        assert result.pages[1].type == ContentType.TOC
        # Verify TOC page content
        toc_page = result.pages[1]
        assert toc_page.title == "Sommaire"
        assert toc_page.id == "toc"

    def test_convert_structure_with_none_sections(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        structure = EbookStructure(meta=meta, cover=cover, sections=None)
        config = EbookConfig(cover_enabled=False, toc=False)

        # When
        result = self.converter.convert_structure_to_pages(structure, config)

        # Then
        assert len(result.pages) == 0

    def test_convert_structure_sets_correct_meta(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        structure = EbookStructure(meta=meta, cover=cover, sections=[])
        config = EbookConfig(format="pdf")

        # When
        result = self.converter.convert_structure_to_pages(structure, config)

        # Then
        assert result.meta["title"] == "Test Title"
        assert result.meta["author"] == "Test Author"
        assert result.meta["engine"] == "weasyprint"
        assert result.meta["format"] == "pdf"

    def test_convert_structure_delegates_to_page_factory(self):
        # Given
        meta = EbookMeta(title="Test Title", author="Test Author")
        cover = EbookCover(title="Test Title")
        section = EbookSection(type="chapter", title="Chapter 1", content="Content 1")
        structure = EbookStructure(meta=meta, cover=cover, sections=[section])
        config = EbookConfig(cover_enabled=True, toc=False)

        # When
        self.converter.convert_structure_to_pages(structure, config)

        # Then - verify calls were made to the fake page factory
        assert len(self.fake_page_factory.created_pages) == 2  # cover + story
        cover_page = self.fake_page_factory.created_pages[0]
        story_page = self.fake_page_factory.created_pages[1]

        assert cover_page.type == ContentType.COVER
        assert cover_page.data["title"] == "Test Title"
        assert story_page.type == ContentType.TEXT
        assert story_page.data["content_html"] == "Content 1"
