from unittest.mock import Mock, patch


from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.page_content import ContentType, EbookPages
from backoffice.domain.services.ebook_page_assembler import EbookPageAssembler


class TestEbookPageAssembler:
    """Test suite for EbookPageAssembler using London methodology"""

    def setup_method(self):
        """Set up test fixtures"""
        self.assembler = EbookPageAssembler()

    @patch("backoffice.domain.services.ebook_page_assembler.create_auto_toc_page")
    def test_create_mixed_ebook_without_toc_and_cover(self, mock_toc):
        # Given
        title = "Mixed Ebook"
        author = "Test Author"
        story_chapters = [{"title": "Chapter 1", "content": "Story content"}]
        coloring_images = [{"url": "image1.jpg"}]
        config = EbookConfig(cover_enabled=False, toc=False)

        # When
        result = self.assembler.create_mixed_ebook(
            title, author, story_chapters, coloring_images, config
        )

        # Then
        assert isinstance(result, EbookPages)
        assert len(result.pages) == 2  # 1 story + 1 coloring
        assert result.pages[0].type == ContentType.TEXT
        assert result.pages[1].type == ContentType.FULL_PAGE_IMAGE
        assert result.meta["type"] == "mixed"
        mock_toc.assert_not_called()

    @patch("backoffice.domain.services.ebook_page_assembler.create_auto_toc_page")
    def test_create_mixed_ebook_with_cover_and_toc(self, mock_toc):
        # Given
        title = "Mixed Ebook"
        author = "Test Author"
        story_chapters = [{"title": "Chapter 1", "content": "Story content"}]
        coloring_images = [{"url": "image1.jpg"}]
        config = EbookConfig(cover_enabled=True, toc=True)

        mock_toc_page = Mock()
        mock_toc.return_value = mock_toc_page

        # When
        result = self.assembler.create_mixed_ebook(
            title, author, story_chapters, coloring_images, config
        )

        # Then
        assert len(result.pages) == 4  # cover + toc + story + coloring
        assert result.pages[0].type == ContentType.COVER
        assert result.pages[1] == mock_toc_page
        assert result.pages[2].type == ContentType.TEXT
        assert result.pages[3].type == ContentType.FULL_PAGE_IMAGE
        mock_toc.assert_called_once()

    @patch("backoffice.domain.services.ebook_page_assembler.create_auto_toc_page")
    def test_create_story_ebook_with_default_config(self, mock_toc):
        # Given
        title = "Story Ebook"
        author = "Test Author"
        chapters = [
            {"title": "Chapter 1", "content": "Content 1"},
            {"title": "Chapter 2", "content": "Content 2"},
        ]

        mock_toc_page = Mock()
        mock_toc.return_value = mock_toc_page

        # When
        result = self.assembler.create_story_ebook(title, author, chapters)

        # Then
        assert len(result.pages) == 4  # cover + toc + 2 chapters
        assert result.pages[0].type == ContentType.COVER
        assert result.pages[1] == mock_toc_page
        assert result.pages[2].type == ContentType.TEXT
        assert result.pages[3].type == ContentType.TEXT
        assert result.meta["type"] == "story"

    def test_create_coloring_ebook_with_custom_config(self):
        # Given
        title = "Coloring Ebook"
        author = "Test Author"
        images = [
            {"url": "image1.jpg", "title": "Image 1"},
            {"url": "image2.jpg", "title": "Image 2"},
        ]
        config = EbookConfig(cover_enabled=True, toc=True)

        # When
        result = self.assembler.create_coloring_ebook(title, author, images, config)

        # Then
        # Only cover + 1 coloring image (first image is used as cover, not duplicated)
        assert len(result.pages) == 2  # cover (with image1) + image2 only
        assert result.pages[0].type == ContentType.COVER
        assert result.pages[0].data["image_url"] == "image1.jpg"  # First image used as cover
        assert result.pages[1].type == ContentType.FULL_PAGE_IMAGE
        assert (
            result.pages[1].data["image_url"] == "image2.jpg"
        )  # Only second image as coloring page
        assert result.meta["type"] == "coloring"

    def test_mix_story_and_coloring_content_equal_length(self):
        # Given
        story_chapters = [
            {"title": "Chapter 1", "content": "Content 1"},
            {"title": "Chapter 2", "content": "Content 2"},
        ]
        coloring_images = [{"url": "image1.jpg"}, {"url": "image2.jpg"}]
        config = EbookConfig()

        # When
        result = self.assembler._mix_story_and_coloring_content(
            story_chapters, coloring_images, config
        )

        # Then
        assert len(result) == 4
        assert result[0].type == ContentType.TEXT
        assert result[1].type == ContentType.FULL_PAGE_IMAGE
        assert result[2].type == ContentType.TEXT
        assert result[3].type == ContentType.FULL_PAGE_IMAGE

    def test_mix_story_and_coloring_content_more_stories(self):
        # Given
        story_chapters = [
            {"title": "Chapter 1", "content": "Content 1"},
            {"title": "Chapter 2", "content": "Content 2"},
            {"title": "Chapter 3", "content": "Content 3"},
        ]
        coloring_images = [{"url": "image1.jpg"}]
        config = EbookConfig()

        # When
        result = self.assembler._mix_story_and_coloring_content(
            story_chapters, coloring_images, config
        )

        # Then
        assert len(result) == 4
        assert result[0].type == ContentType.TEXT  # Chapter 1
        assert result[1].type == ContentType.FULL_PAGE_IMAGE  # Image 1
        assert result[2].type == ContentType.TEXT  # Chapter 2
        assert result[3].type == ContentType.TEXT  # Chapter 3

    def test_mix_story_and_coloring_content_more_images(self):
        # Given
        story_chapters = [{"title": "Chapter 1", "content": "Content 1"}]
        coloring_images = [
            {"url": "image1.jpg"},
            {"url": "image2.jpg"},
            {"url": "image3.jpg"},
        ]
        config = EbookConfig()

        # When
        result = self.assembler._mix_story_and_coloring_content(
            story_chapters, coloring_images, config
        )

        # Then
        assert len(result) == 4
        assert result[0].type == ContentType.TEXT  # Chapter 1
        assert result[1].type == ContentType.FULL_PAGE_IMAGE  # Image 1
        assert result[2].type == ContentType.FULL_PAGE_IMAGE  # Image 2
        assert result[3].type == ContentType.FULL_PAGE_IMAGE  # Image 3

    def test_mix_story_and_coloring_content_empty_lists(self):
        # Given
        story_chapters = []
        coloring_images = []
        config = EbookConfig()

        # When
        result = self.assembler._mix_story_and_coloring_content(
            story_chapters, coloring_images, config
        )

        # Then
        assert len(result) == 0

    def test_create_story_ebook_delegates_to_page_factory(self):
        # Given
        title = "Story Ebook"
        author = "Test Author"
        chapters = [{"title": "Chapter 1", "content": "Content 1"}]
        config = EbookConfig(cover_enabled=True, toc=False)

        # When
        result = self.assembler.create_story_ebook(title, author, chapters, config)

        # Then
        assert isinstance(result, EbookPages)
        assert result.meta["title"] == title
        assert result.meta["author"] == author
        assert result.meta["type"] == "story"
        assert len(result.pages) > 0  # Should have at least cover + chapter page

    def test_create_mixed_ebook_uses_default_config_when_none(self):
        # Given
        title = "Mixed Ebook"
        author = "Test Author"
        story_chapters = []
        coloring_images = []

        # When
        result = self.assembler.create_mixed_ebook(
            title, author, story_chapters, coloring_images, None
        )

        # Then
        assert isinstance(result, EbookPages)
        assert result.meta["format"] == "pdf"  # Default from EbookConfig()

    def test_create_story_ebook_meta_includes_all_fields(self):
        # Given
        title = "Story Ebook"
        author = "Test Author"
        chapters = []
        config = EbookConfig(format="epub")

        # When
        result = self.assembler.create_story_ebook(title, author, chapters, config)

        # Then
        assert result.meta["title"] == title
        assert result.meta["author"] == author
        assert result.meta["engine"] == "weasyprint"
        assert result.meta["format"] == "epub"
        assert result.meta["type"] == "story"
