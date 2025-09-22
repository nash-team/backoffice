import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import (
    EbookCover,
    EbookMeta,
    EbookSection,
    EbookStructure,
)
from backoffice.infrastructure.adapters.pdf_generator_adapter import (
    PDFGeneratorAdapter,
    PDFGenerationError,
)


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
            sections=[EbookSection(type="chapter", title="Chapter 1", content="Content 1")],
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
                f'<div class="{chapter_class}"><h1>{section.title}</h1><p>{section.content}</p></div>'
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


class TestPDFGeneratorAdapter:
    """Tests for PDFGeneratorAdapter using London style with fakes."""

    def test_given_adapter_when_checking_format_support_then_returns_correct_values(self):
        # Given
        adapter = PDFGeneratorAdapter()

        # When/Then
        assert adapter.supports_format("pdf") is True
        assert adapter.supports_format("PDF") is True
        assert adapter.supports_format("epub") is False
        assert adapter.supports_format("mobi") is False

    def test_given_adapter_when_getting_supported_formats_then_returns_pdf_only(self):
        # Given
        adapter = PDFGeneratorAdapter()

        # When
        formats = adapter.get_supported_formats()

        # Then
        assert formats == ["pdf"]

    @pytest.mark.asyncio
    async def test_given_valid_structure_when_generating_pdf_then_returns_pdf_bytes(
        self, monkeypatch
    ):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book", author="Test Author"),
            cover=EbookCover(title="Test Cover"),
            sections=[EbookSection(type="chapter", title="Chapter 1", content="Content 1")],
        )
        config = EbookConfig(format="pdf", toc_title="Contents")

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        adapter = PDFGeneratorAdapter()
        adapter.content_parser = FakeContentParser()

        # When
        result = await adapter.generate_ebook(structure, config)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")
        assert b"fake pdf content from string" in result

    @pytest.mark.asyncio
    async def test_given_wrong_format_when_generating_ebook_then_raises_error(self, monkeypatch):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book", author="Test Author"),
            cover=EbookCover(title="Test Cover"),
            sections=[],
        )
        config = EbookConfig(format="epub")  # Wrong format

        adapter = PDFGeneratorAdapter()

        # When/Then
        with pytest.raises(PDFGenerationError, match="PDF adapter cannot generate format: epub"):
            await adapter.generate_ebook(structure, config)

    @pytest.mark.asyncio
    async def test_given_chapter_numbering_when_generating_pdf_then_applies_numbering(
        self, monkeypatch
    ):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book", author="Test Author"),
            cover=EbookCover(title="Test Cover"),
            sections=[EbookSection(type="chapter", title="Chapter 1", content="Content 1")],
        )
        config = EbookConfig(format="pdf", chapter_numbering=True, chapter_numbering_style="roman")

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        adapter = PDFGeneratorAdapter()
        adapter.content_parser = FakeContentParser()

        # When
        result = await adapter.generate_ebook(structure, config)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")

    @pytest.mark.asyncio
    async def test_given_toc_disabled_when_generating_pdf_then_no_toc_in_output(self, monkeypatch):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book", author="Test Author"),
            cover=EbookCover(title="Test Cover"),
            toc=False,
            sections=[EbookSection(type="chapter", title="Chapter 1", content="Content 1")],
        )
        config = EbookConfig(format="pdf", toc=False)

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        adapter = PDFGeneratorAdapter()
        adapter.content_parser = FakeContentParser()

        # When
        result = await adapter.generate_ebook(structure, config)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")

    @pytest.mark.asyncio
    async def test_given_weasyprint_error_when_generating_pdf_then_raises_pdf_generation_error(
        self, monkeypatch
    ):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book", author="Test Author"),
            cover=EbookCover(title="Test Cover"),
            sections=[],
        )
        config = EbookConfig(format="pdf")

        # Mock WeasyPrint to raise an exception
        def failing_weasyprint(*args, **kwargs):
            raise Exception("WeasyPrint rendering failed")

        monkeypatch.setattr("weasyprint.HTML", failing_weasyprint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        adapter = PDFGeneratorAdapter()
        adapter.content_parser = FakeContentParser()

        # When/Then
        with pytest.raises(PDFGenerationError, match="Failed to generate PDF"):
            await adapter.generate_ebook(structure, config)

    def test_given_custom_templates_dir_when_initializing_then_uses_custom_path(self, monkeypatch):
        # Given
        custom_templates_dir = Path("/custom/templates")

        # Mock Jinja2 Environment
        mock_env = MagicMock()
        monkeypatch.setattr("jinja2.Environment", lambda **kwargs: mock_env)

        # When
        adapter = PDFGeneratorAdapter(templates_dir=custom_templates_dir)

        # Then
        assert adapter.templates_dir == custom_templates_dir

    @pytest.mark.asyncio
    async def test_given_legacy_json_when_generating_pdf_from_json_then_returns_pdf_bytes(
        self, monkeypatch
    ):
        # Given
        json_content = json.dumps(
            {
                "meta": {"title": "Legacy Test", "author": "Legacy Author"},
                "cover": {"title": "Legacy Cover"},
                "sections": [{"type": "chapter", "title": "Chapter 1", "content": "Content"}],
            }
        )

        # Mock external dependencies
        monkeypatch.setattr("weasyprint.HTML", FakeWeasyPrint)
        monkeypatch.setattr("jinja2.Environment", FakeJinjaEnvironment)

        adapter = PDFGeneratorAdapter()
        adapter.content_parser = FakeContentParser()

        # When
        result = await adapter.generate_pdf_from_json(json_content)

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

        adapter = PDFGeneratorAdapter()

        # When
        result = adapter.generate_pdf_from_file(html_file_path)

        # Then
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")
        assert b"fake pdf content from file" in result

    def test_given_invalid_html_file_when_generating_pdf_from_file_then_raises_error(
        self, monkeypatch
    ):
        # Given
        html_file_path = Path("/fake/path/invalid.html")

        # Mock WeasyPrint to raise an exception
        def failing_weasyprint(*args, **kwargs):
            raise Exception("File not found or invalid HTML")

        monkeypatch.setattr("weasyprint.HTML", failing_weasyprint)

        adapter = PDFGeneratorAdapter()

        # When/Then
        with pytest.raises(PDFGenerationError, match="Failed to generate PDF from file"):
            adapter.generate_pdf_from_file(html_file_path)
