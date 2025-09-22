from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookCover, EbookMeta, EbookStructure
from backoffice.domain.entities.page_content import ContentType, PageLayout
from backoffice.domain.services.page_factory import PageFactory


class TestPageFactory:
    """Test suite for PageFactory using London methodology"""

    def test_create_cover_page_with_minimal_data(self):
        # Given
        title = "Test Title"
        author = "Test Author"

        # When
        page = PageFactory.create_cover_page(title, author)

        # Then
        assert page.type == ContentType.COVER
        assert page.template == "story"
        assert page.layout == PageLayout.COVER
        assert page.data["title"] == title
        assert page.data["author"] == author
        assert page.data["subtitle"] is None
        assert page.data["image_url"] is None
        assert page.id == "cover"
        assert page.title == "Couverture"
        assert page.display_in_toc is False
        assert page.page_break_after is True

    def test_create_cover_page_with_all_data(self):
        # Given
        title = "Test Title"
        author = "Test Author"
        template = "coloring"
        subtitle = "Test Subtitle"
        image_url = "http://example.com/image.jpg"

        # When
        page = PageFactory.create_cover_page(title, author, template, subtitle, image_url)

        # Then
        assert page.template == template
        assert page.data["subtitle"] == subtitle
        assert page.data["image_url"] == image_url

    def test_create_story_page_with_minimal_data(self):
        # Given
        content_html = "<p>Test content</p>"
        title = "Chapter 1"
        page_id = "chapter-1"

        # When
        page = PageFactory.create_story_page(content_html, title, page_id)

        # Then
        assert page.type == ContentType.TEXT
        assert page.template == "story"
        assert page.layout == PageLayout.STANDARD
        assert page.data["content_html"] == content_html
        assert page.data["chapter_number"] is None
        assert page.id == page_id
        assert page.title == title
        assert page.display_in_toc is True
        assert page.page_break_before is True

    def test_create_story_page_with_chapter_number(self):
        # Given
        content_html = "<p>Test content</p>"
        title = "Chapter 1"
        page_id = "chapter-1"
        template = "chapter"
        chapter_number = 1

        # When
        page = PageFactory.create_story_page(content_html, title, page_id, template, chapter_number)

        # Then
        assert page.template == template
        assert page.data["chapter_number"] == chapter_number

    def test_create_coloring_page_with_minimal_data(self):
        # Given
        image_url = "http://example.com/coloring.jpg"
        page_id = "coloring-1"

        # When
        page = PageFactory.create_coloring_page(image_url, page_id)

        # Then
        assert page.type == ContentType.FULL_PAGE_IMAGE
        assert page.template == "coloring"
        assert page.layout == PageLayout.FULL_BLEED
        assert page.data["image_url"] == image_url
        assert page.data["alt_text"] == "Image à colorier"
        assert page.id == page_id
        assert page.title == "Coloriage"
        assert page.display_in_toc is True
        assert page.page_break_before is True

    def test_create_coloring_page_with_all_data(self):
        # Given
        image_url = "http://example.com/coloring.jpg"
        page_id = "coloring-1"
        title = "Custom Coloring Title"
        alt_text = "Custom alt text"
        display_in_toc = False

        # When
        page = PageFactory.create_coloring_page(image_url, page_id, title, alt_text, display_in_toc)

        # Then
        assert page.title == title
        assert page.data["alt_text"] == alt_text
        assert page.display_in_toc == display_in_toc

    def test_create_cover_from_structure_uses_structure_data(self):
        # Given
        meta = EbookMeta(title="Structure Title", author="Structure Author")
        cover = EbookCover(title="Structure Title")
        structure = EbookStructure(meta=meta, cover=cover, sections=[])
        config = EbookConfig()

        # When
        page = PageFactory.create_cover_from_structure(structure, config)

        # Then
        assert page.data["title"] == "Structure Title"
        assert page.data["author"] == "Structure Author"

    def test_create_cover_from_structure_uses_title_override(self):
        # Given
        meta = EbookMeta(title="Structure Title", author="Structure Author")
        cover = EbookCover(title="Structure Title")
        structure = EbookStructure(meta=meta, cover=cover, sections=[])
        config = EbookConfig(cover_title_override="Override Title")

        # When
        page = PageFactory.create_cover_from_structure(structure, config)

        # Then
        assert page.data["title"] == "Override Title"
        assert page.data["author"] == "Structure Author"

    def test_create_story_from_section_without_numbering(self):
        # Given
        section = type("Section", (), {"content": "<p>Content</p>", "title": "Chapter"})()
        section_index = 1
        config = EbookConfig(chapter_numbering=False)

        # When
        page = PageFactory.create_story_from_section(section, section_index, config)

        # Then
        assert page.data["content_html"] == "<p>Content</p>"
        assert page.title == "Chapter"
        assert page.id == "chapter-1"
        assert page.data["chapter_number"] is None

    def test_create_story_from_section_with_numbering(self):
        # Given
        section = type("Section", (), {"content": "<p>Content</p>", "title": "Chapter"})()
        section_index = 2
        config = EbookConfig(chapter_numbering=True)

        # When
        page = PageFactory.create_story_from_section(section, section_index, config)

        # Then
        assert page.data["chapter_number"] == 2

    def test_create_story_from_section_with_custom_template(self):
        # Given
        section = type("Section", (), {"content": "<p>Content</p>", "title": "Chapter"})()
        section_index = 1
        config = EbookConfig()
        template = "custom_template"

        # When
        page = PageFactory.create_story_from_section(section, section_index, config, template)

        # Then
        assert page.template == template
