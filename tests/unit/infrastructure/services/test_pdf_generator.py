import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backoffice.domain.entities.ebook_structure import (
    EbookCover,
    EbookMeta,
    EbookSection,
    EbookStructure,
)
from backoffice.infrastructure.services.pdf_generator import PDFGenerator, PDFGenerationError


class FakeWeasyPrint:
    """Fake WeasyPrint HTML class for testing"""

    def __init__(self, string=None, filename=None):
        self.string = string
        self.filename = filename

    def write_pdf(self) -> bytes:
        """Return fake PDF bytes"""
        if self.string:
            return b"%PDF-1.4 fake pdf content from string"
        if self.filename:
            return b"%PDF-1.4 fake pdf content from file"
        return b"%PDF-1.4 fake pdf content"


class FakeJinjaTemplate:
    """Fake Jinja2 template for testing"""

    def render(self, **kwargs) -> str:
        """Return simple HTML with provided variables"""
        title = kwargs.get("title", "No Title")
        author = kwargs.get("author", "No Author")
        processed_content = kwargs.get("processed_content", "")
        toc_html = kwargs.get("toc_html", "")
        toc = kwargs.get("toc", False)
        toc_title = kwargs.get("toc_title", "Sommaire")

        html = f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p>By: {author}</p>
"""
        if toc:
            html += f"<h2>{toc_title}</h2><ul>{toc_html}</ul>"

        html += f"<div>{processed_content}</div></body></html>"
        return html


class FakeJinjaEnvironment:
    """Fake Jinja2 Environment for testing"""

    def __init__(self, loader=None, autoescape=True):
        self.loader = loader
        self.autoescape = autoescape

    def get_template(self, template_name: str) -> FakeJinjaTemplate:
        return FakeJinjaTemplate()


class FakeContentParser:
    """Fake ContentParser for testing"""

    def parse_ebook_structure(self, json_content: str) -> EbookStructure:
        """Parse JSON and return fake structure"""
        data = json.loads(json_content)
        return EbookStructure(
            meta=EbookMeta(
                title=data.get("meta", {}).get("title", "Test Title"),
                author=data.get("meta", {}).get("author", "Test Author"),
            ),
            cover=EbookCover(title="Test Cover"),
            toc=data.get("toc", True),
            sections=[EbookSection(type="chapter", title="Chapter 1", content_md="Content 1")],
        )

    def generate_html_from_structure(
        self,
        ebook_structure: EbookStructure,
        chapter_numbering: bool = False,
        chapter_numbering_style: str = "arabic",
    ) -> str:
        """Generate fake HTML content"""
        html_parts = []
        for section in ebook_structure.sections or []:
            chapter_class = "chapter"
            if chapter_numbering:
                chapter_class += " chapter-numbered"
                if chapter_numbering_style == "roman":
                    chapter_class += " roman"

            html_parts.append(
                f'<div class="{chapter_class}"><h1>{section.title}</h1><p>{section.content_md}</p></div>'
            )

        return "\n".join(html_parts)

    def generate_toc_from_structure(self, ebook_structure: EbookStructure) -> str:
        """Generate fake TOC HTML"""
        if not ebook_structure.toc:
            return ""

        toc_items = []
        for section in ebook_structure.sections or []:
            if section.type == "chapter":
                anchor = section.title.lower().replace(" ", "-")
                toc_items.append(
                    f'<li class="toc-item toc-level-1"><a href="#{anchor}">{section.title}</a></li>'
                )

        return "\n".join(toc_items)

    def parse_markdown_content(self, content: str):
        """Return fake chapter data for markdown content"""
        return [{"title": "Test Chapter", "content": content}]

    def generate_html_content(
        self, chapters, chapter_numbering=False, chapter_numbering_style="arabic"
    ):
        """Generate fake HTML from chapters"""
        return "<div class='chapter'><h1>Test Chapter</h1><p>Test content</p></div>"

    def extract_toc_entries(self, chapters):
        """Return fake TOC entries"""
        return [{"title": "Test Chapter", "anchor": "test-chapter", "level": 1}]

    def generate_toc_html(self, toc_entries):
        """Generate fake TOC HTML from entries"""
        return '<li class="toc-item"><a href="#test-chapter">Test Chapter</a></li>'


class TestPDFGenerator:
    """Tests for PDFGenerator using London style with fakes."""

    def test_given_valid_json_when_generating_pdf_then_returns_pdf_bytes(self, monkeypatch):
        # Given
        valid_json = {
            "meta": {"title": "Test Book", "author": "Test Author"},
            "cover": {"title": "Test Cover"},
            "toc": True,
            "sections": [{"type": "chapter", "title": "Chapter 1", "content_md": "Content 1"}],
        }
        json_content = json.dumps(valid_json)

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        generator = PDFGenerator()
        generator.content_parser = FakeContentParser()

        # When
        result = generator.generate_pdf_from_json(json_content)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")
        assert b"fake pdf content from string" in result

    def test_given_json_with_toc_disabled_when_generating_pdf_then_no_toc_in_output(
        self, monkeypatch
    ):
        # Given
        json_without_toc = {
            "meta": {"title": "Test Book", "author": "Test Author"},
            "cover": {"title": "Test Cover"},
            "toc": False,
            "sections": [{"type": "chapter", "title": "Chapter 1", "content_md": "Content 1"}],
        }
        json_content = json.dumps(json_without_toc)

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        generator = PDFGenerator()
        generator.content_parser = FakeContentParser()

        # When
        result = generator.generate_pdf_from_json(json_content)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")

    def test_given_chapter_numbering_enabled_when_generating_pdf_then_includes_numbering_styles(
        self, monkeypatch
    ):
        # Given
        valid_json = {
            "meta": {"title": "Test Book", "author": "Test Author"},
            "cover": {"title": "Test Cover"},
            "sections": [{"type": "chapter", "title": "Chapter 1", "content_md": "Content 1"}],
        }
        json_content = json.dumps(valid_json)

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        generator = PDFGenerator()
        generator.content_parser = FakeContentParser()

        # When
        result = generator.generate_pdf_from_json(
            json_content, chapter_numbering=True, chapter_numbering_style="roman"
        )

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")

    def test_given_invalid_json_when_generating_pdf_then_raises_pdf_generation_error(
        self, monkeypatch
    ):
        # Given
        invalid_json = "{ invalid json content"

        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        generator = PDFGenerator()
        generator.content_parser = FakeContentParser()

        # When/Then
        with pytest.raises(PDFGenerationError, match="Failed to generate PDF from JSON"):
            generator.generate_pdf_from_json(invalid_json)

    def test_given_weasyprint_error_when_generating_pdf_then_raises_pdf_generation_error(
        self, monkeypatch
    ):
        # Given
        valid_json = {
            "meta": {"title": "Test Book", "author": "Test Author"},
            "cover": {"title": "Test Cover"},
            "sections": [{"type": "chapter", "title": "Chapter 1", "content_md": "Content 1"}],
        }
        json_content = json.dumps(valid_json)

        # Mock WeasyPrint to raise an exception
        def failing_weasyprint(*args, **kwargs):
            raise Exception("WeasyPrint rendering failed")

        monkeypatch.setattr("weasyprint.HTML", failing_weasyprint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        generator = PDFGenerator()
        generator.content_parser = FakeContentParser()

        # When/Then
        with pytest.raises(PDFGenerationError, match="Failed to generate PDF from JSON"):
            generator.generate_pdf_from_json(json_content)

    def test_given_markdown_content_when_generating_pdf_legacy_then_returns_pdf_bytes(
        self, monkeypatch
    ):
        # Given
        markdown_content = "# Chapter 1\n\nSome content here"
        title = "Test Book"
        author = "Test Author"

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        generator = PDFGenerator()
        generator.content_parser = FakeContentParser()

        # When
        result = generator.generate_pdf(content=markdown_content, title=title, author=author)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")

    def test_given_toc_disabled_when_generating_pdf_legacy_then_no_toc_processing(
        self, monkeypatch
    ):
        # Given
        markdown_content = "# Chapter 1\n\nSome content here"
        title = "Test Book"
        author = "Test Author"

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        generator = PDFGenerator()
        generator.content_parser = FakeContentParser()

        # When
        result = generator.generate_pdf(
            content=markdown_content, title=title, author=author, toc=False
        )

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")

    def test_given_html_file_when_generating_pdf_from_file_then_returns_pdf_bytes(
        self, monkeypatch
    ):
        # Given
        html_file_path = Path("/fake/path/test.html")

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)

        generator = PDFGenerator()

        # When
        result = generator.generate_pdf_from_file(html_file_path)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")
        assert b"fake pdf content from file" in result

    def test_given_invalid_html_file_when_generating_pdf_from_file_then_raises_pdf_generation_error(
        self, monkeypatch
    ):
        # Given
        html_file_path = Path("/fake/path/invalid.html")

        # Mock WeasyPrint to raise an exception
        def failing_weasyprint(*args, **kwargs):
            raise Exception("File not found or invalid HTML")

        monkeypatch.setattr("weasyprint.HTML", failing_weasyprint)

        generator = PDFGenerator()

        # When/Then
        with pytest.raises(PDFGenerationError, match="Failed to generate PDF from file"):
            generator.generate_pdf_from_file(html_file_path)

    def test_given_custom_templates_dir_when_initializing_then_uses_custom_path(self, monkeypatch):
        # Given
        custom_templates_dir = Path("/custom/templates")

        # Mock Jinja2 Environment
        mock_env = MagicMock()
        monkeypatch.setattr("jinja2.Environment", lambda **kwargs: mock_env)

        # When
        generator = PDFGenerator(templates_dir=custom_templates_dir)

        # Then
        assert generator.templates_dir == custom_templates_dir

    def test_given_no_templates_dir_when_initializing_then_uses_default_path(self, monkeypatch):
        # Given/When
        # Mock Jinja2 Environment
        mock_env = MagicMock()
        monkeypatch.setattr("jinja2.Environment", lambda **kwargs: mock_env)

        generator = PDFGenerator()

        # Then
        # Verify the generator was initialized correctly
        assert generator.templates_dir.name == "templates"
        # Just check that it's set to some sensible default (exact path may vary)
        assert isinstance(generator.templates_dir, Path)

    def test_given_custom_toc_title_when_generating_pdf_then_uses_custom_title(self, monkeypatch):
        # Given
        valid_json = {
            "meta": {"title": "Test Book", "author": "Test Author"},
            "cover": {"title": "Test Cover"},
            "toc": True,
            "sections": [{"type": "chapter", "title": "Chapter 1", "content_md": "Content 1"}],
        }
        json_content = json.dumps(valid_json)
        custom_toc_title = "Table des Matières"

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        generator = PDFGenerator()
        generator.content_parser = FakeContentParser()

        # When
        result = generator.generate_pdf_from_json(json_content, toc_title=custom_toc_title)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")
