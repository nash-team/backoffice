from pathlib import Path
from unittest.mock import Mock, patch


from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.entities.page_content import EbookPages
from backoffice.domain.services.modular_page_generator import ModularPageGenerator


class TestModularPageGenerator:
    """Test suite for refactored ModularPageGenerator using London methodology"""

    def setup_method(self):
        """Set up test fixtures"""
        self.templates_dir = Path("/fake/templates")

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_init_creates_all_dependencies(self, mock_pdf_renderer, mock_assembler, mock_converter):
        # When
        generator = ModularPageGenerator(self.templates_dir)

        # Then
        assert generator.templates_dir == self.templates_dir
        mock_converter.assert_called_once()
        mock_assembler.assert_called_once()
        mock_pdf_renderer.assert_called_once_with(self.templates_dir)

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_convert_structure_to_pages_delegates_to_converter(
        self, mock_pdf_renderer, mock_assembler, mock_converter
    ):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        structure = Mock(spec=EbookStructure)
        config = Mock(spec=EbookConfig)
        expected_result = Mock(spec=EbookPages)

        # Mock converter
        mock_converter_instance = Mock()
        mock_converter.return_value = mock_converter_instance
        mock_converter_instance.convert_structure_to_pages.return_value = expected_result

        # When
        result = generator.convert_structure_to_pages(structure, config)

        # Then
        assert result == expected_result
        mock_converter_instance.convert_structure_to_pages.assert_called_once_with(
            structure, config
        )

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_create_mixed_ebook_delegates_to_assembler(
        self, mock_pdf_renderer, mock_assembler, mock_converter
    ):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        title = "Mixed Ebook"
        author = "Test Author"
        story_chapters = [{"title": "Chapter 1", "content": "Content"}]
        coloring_images = [{"url": "image.jpg"}]
        config = Mock(spec=EbookConfig)
        expected_result = Mock(spec=EbookPages)

        # Mock assembler
        mock_assembler_instance = Mock()
        mock_assembler.return_value = mock_assembler_instance
        mock_assembler_instance.create_mixed_ebook.return_value = expected_result

        # When
        result = generator.create_mixed_ebook(
            title, author, story_chapters, coloring_images, config
        )

        # Then
        assert result == expected_result
        mock_assembler_instance.create_mixed_ebook.assert_called_once_with(
            title, author, story_chapters, coloring_images, config
        )

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_create_story_ebook_delegates_to_assembler(
        self, mock_pdf_renderer, mock_assembler, mock_converter
    ):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        title = "Story Ebook"
        author = "Test Author"
        chapters = [{"title": "Chapter 1", "content": "Content"}]
        config = Mock(spec=EbookConfig)
        expected_result = Mock(spec=EbookPages)

        # Mock assembler
        mock_assembler_instance = Mock()
        mock_assembler.return_value = mock_assembler_instance
        mock_assembler_instance.create_story_ebook.return_value = expected_result

        # When
        result = generator.create_story_ebook(title, author, chapters, config)

        # Then
        assert result == expected_result
        mock_assembler_instance.create_story_ebook.assert_called_once_with(
            title, author, chapters, config
        )

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_create_coloring_ebook_delegates_to_assembler(
        self, mock_pdf_renderer, mock_assembler, mock_converter
    ):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        title = "Coloring Ebook"
        author = "Test Author"
        images = [{"url": "image1.jpg"}, {"url": "image2.jpg"}]
        config = Mock(spec=EbookConfig)
        expected_result = Mock(spec=EbookPages)

        # Mock assembler
        mock_assembler_instance = Mock()
        mock_assembler.return_value = mock_assembler_instance
        mock_assembler_instance.create_coloring_ebook.return_value = expected_result

        # When
        result = generator.create_coloring_ebook(title, author, images, config)

        # Then
        assert result == expected_result
        mock_assembler_instance.create_coloring_ebook.assert_called_once_with(
            title, author, images, config
        )

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_generate_pdf_from_pages_delegates_to_renderer(
        self, mock_pdf_renderer, mock_assembler, mock_converter
    ):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        ebook = Mock(spec=EbookPages)
        expected_result = b"fake pdf bytes"

        # Mock PDF renderer
        mock_renderer_instance = Mock()
        mock_pdf_renderer.return_value = mock_renderer_instance
        mock_renderer_instance.generate_pdf_from_pages.return_value = expected_result

        # When
        result = generator.generate_pdf_from_pages(ebook)

        # Then
        assert result == expected_result
        mock_renderer_instance.generate_pdf_from_pages.assert_called_once_with(ebook)

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_create_mixed_ebook_with_none_config(
        self, mock_pdf_renderer, mock_assembler, mock_converter
    ):
        # Given
        generator = ModularPageGenerator(self.templates_dir)
        title = "Mixed Ebook"
        author = "Test Author"
        story_chapters = []
        coloring_images = []

        # Mock assembler
        mock_assembler_instance = Mock()
        mock_assembler.return_value = mock_assembler_instance

        # When
        generator.create_mixed_ebook(title, author, story_chapters, coloring_images, None)

        # Then
        mock_assembler_instance.create_mixed_ebook.assert_called_once_with(
            title, author, story_chapters, coloring_images, None
        )

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_init_with_string_path(self, mock_pdf_renderer, mock_assembler, mock_converter):
        # Given
        templates_dir = "/test/templates"

        # When
        generator = ModularPageGenerator(templates_dir)

        # Then
        assert generator.templates_dir == Path(templates_dir)

    @patch("backoffice.domain.services.modular_page_generator.EbookStructureConverter")
    @patch("backoffice.domain.services.modular_page_generator.EbookPageAssembler")
    @patch("backoffice.domain.services.modular_page_generator.PdfRenderer")
    def test_init_with_path_object(self, mock_pdf_renderer, mock_assembler, mock_converter):
        # Given
        templates_dir = Path("/test/templates")

        # When
        generator = ModularPageGenerator(templates_dir)

        # Then
        assert generator.templates_dir == templates_dir
