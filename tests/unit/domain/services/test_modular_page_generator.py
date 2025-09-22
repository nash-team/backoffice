from pathlib import Path

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure, EbookMeta, EbookCover
from backoffice.domain.entities.page_content import EbookPages
from backoffice.domain.services.modular_page_generator import ModularPageGenerator


class TestModularPageGenerator:
    """Test suite for refactored ModularPageGenerator using London methodology"""

    def setup_method(self):
        """Set up test fixtures"""
        self.templates_dir = Path("/fake/templates")

    def test_init_creates_all_dependencies(self):
        # When
        generator = ModularPageGenerator(self.templates_dir)

        # Then
        assert generator.templates_dir == self.templates_dir
        assert generator.converter is not None
        assert generator.assembler is not None
        assert generator.pdf_renderer is not None

    def test_convert_structure_to_pages_delegates_to_converter(self):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        meta = EbookMeta(title="Test Book", author="Test Author")
        cover = EbookCover(title="Test Book")
        structure = EbookStructure(meta=meta, cover=cover, sections=[])
        config = EbookConfig()

        # When
        result = generator.convert_structure_to_pages(structure, config)

        # Then
        assert isinstance(result, EbookPages)
        assert result.meta["title"] == "Test Book"
        assert result.meta["author"] == "Test Author"

    def test_create_mixed_ebook_delegates_to_assembler(self):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        title = "Mixed Ebook"
        author = "Test Author"
        story_chapters = [{"title": "Chapter 1", "content": "Story content"}]
        coloring_images = [{"url": "image.jpg", "title": "Image 1"}]
        config = EbookConfig()

        # When
        result = generator.create_mixed_ebook(
            title, author, story_chapters, coloring_images, config
        )

        # Then
        assert isinstance(result, EbookPages)
        assert result.meta["title"] == title
        assert result.meta["author"] == author
        assert result.meta["type"] == "mixed"
        assert len(result.pages) > 0

    def test_create_story_ebook_delegates_to_assembler(self):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        title = "Story Ebook"
        author = "Test Author"
        chapters = [{"title": "Chapter 1", "content": "Story content"}]
        config = EbookConfig()

        # When
        result = generator.create_story_ebook(title, author, chapters, config)

        # Then
        assert isinstance(result, EbookPages)
        assert result.meta["title"] == title
        assert result.meta["author"] == author
        assert result.meta["type"] == "story"
        assert len(result.pages) > 0

    def test_create_coloring_ebook_delegates_to_assembler(self):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        title = "Coloring Ebook"
        author = "Test Author"
        images = [
            {"url": "image1.jpg", "title": "Image 1"},
            {"url": "image2.jpg", "title": "Image 2"},
        ]
        config = EbookConfig()

        # When
        result = generator.create_coloring_ebook(title, author, images, config)

        # Then
        assert isinstance(result, EbookPages)
        assert result.meta["title"] == title
        assert result.meta["author"] == author
        assert result.meta["type"] == "coloring"
        assert len(result.pages) > 0

    def test_generate_pdf_from_pages_delegates_to_renderer(self):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        ebook = EbookPages(meta={"title": "Test Ebook", "author": "Test Author"}, pages=[])

        # When
        result = generator.generate_pdf_from_pages(ebook)

        # Then
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_create_mixed_ebook_with_none_config(self):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        title = "Mixed Ebook"
        author = "Test Author"
        story_chapters = []
        coloring_images = []

        # When
        result = generator.create_mixed_ebook(title, author, story_chapters, coloring_images, None)

        # Then
        assert isinstance(result, EbookPages)
        assert result.meta["title"] == title
        assert result.meta["author"] == author

    def test_init_with_string_path(self):
        # Given
        templates_dir = "/test/templates"

        # When
        generator = ModularPageGenerator(templates_dir)

        # Then
        assert generator.templates_dir == Path(templates_dir)

    def test_init_with_path_object(self):
        # Given
        templates_dir = Path("/test/templates")

        # When
        generator = ModularPageGenerator(templates_dir)

        # Then
        assert generator.templates_dir == templates_dir
