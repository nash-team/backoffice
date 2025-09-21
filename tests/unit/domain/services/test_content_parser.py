import json
import pytest

from backoffice.domain.entities.ebook_structure import (
    EbookCover,
    EbookMeta,
    EbookSection,
    EbookStructure,
)
from backoffice.domain.services.content_parser import ContentParser


class TestContentParser:
    """Tests for ContentParser using London style with fakes."""

    def test_given_valid_json_when_parsing_structure_then_returns_ebook_structure(self):
        # Given
        valid_json = {
            "meta": {"title": "Test Book", "author": "Test Author", "language": "fr"},
            "cover": {"title": "Test Cover", "subtitle": "A test book"},
            "toc": True,
            "sections": [
                {"type": "chapter", "title": "Chapter 1", "content_md": "Content of chapter 1"}
            ],
            "back_cover": {"blurb": "A test blurb", "about_author": "About the author"},
        }
        json_content = json.dumps(valid_json)
        parser = ContentParser()

        # When
        result = parser.parse_ebook_structure(json_content)

        # Then
        assert isinstance(result, EbookStructure)
        assert result.meta.title == "Test Book"
        assert result.meta.author == "Test Author"
        assert result.cover.title == "Test Cover"
        assert result.toc is True
        assert len(result.sections) == 1
        assert result.sections[0].title == "Chapter 1"
        assert result.back_cover.blurb == "A test blurb"

    def test_given_invalid_json_when_parsing_structure_then_raises_value_error(self):
        # Given
        invalid_json = "{ invalid json content"
        parser = ContentParser()

        # When/Then
        with pytest.raises(ValueError, match="Invalid ebook JSON structure"):
            parser.parse_ebook_structure(invalid_json)

    def test_given_minimal_json_when_parsing_structure_then_uses_defaults(self):
        # Given
        minimal_json = {"meta": {"title": "Minimal Book"}, "cover": {"title": "Minimal Cover"}}
        json_content = json.dumps(minimal_json)
        parser = ContentParser()

        # When
        result = parser.parse_ebook_structure(json_content)

        # Then
        assert result.meta.title == "Minimal Book"
        assert result.meta.author == "Assistant IA"  # default
        assert result.toc is True  # default
        assert len(result.sections) == 0  # empty by default
        assert result.back_cover is None  # not provided

    def test_given_ebook_structure_when_generating_html_then_creates_chapter_divs(self):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book"),
            cover=EbookCover(title="Test Cover"),
            sections=[
                EbookSection(type="chapter", title="Chapter 1", content_md="Content 1"),
                EbookSection(type="chapter", title="Chapter 2", content_md="Content 2"),
            ],
        )
        parser = ContentParser()

        # When
        result = parser.generate_html_from_structure(structure)

        # Then
        assert '<div class="chapter"' in result
        assert "<h1>Chapter 1</h1>" in result
        assert "<h1>Chapter 2</h1>" in result
        assert "<p>Content 1</p>" in result
        assert "<p>Content 2</p>" in result

    def test_given_chapter_numbering_enabled_when_generating_html_then_adds_numbered_classes(self):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book"),
            cover=EbookCover(title="Test Cover"),
            sections=[EbookSection(type="chapter", title="Chapter 1", content_md="Content 1")],
        )
        parser = ContentParser()

        # When
        result = parser.generate_html_from_structure(
            structure, chapter_numbering=True, chapter_numbering_style="arabic"
        )

        # Then
        assert '<div class="chapter chapter-numbered"' in result

    def test_given_roman_numbering_when_generating_html_then_adds_roman_class(self):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book"),
            cover=EbookCover(title="Test Cover"),
            sections=[EbookSection(type="chapter", title="Chapter 1", content_md="Content 1")],
        )
        parser = ContentParser()

        # When
        result = parser.generate_html_from_structure(
            structure, chapter_numbering=True, chapter_numbering_style="roman"
        )

        # Then
        assert '<div class="chapter chapter-numbered roman"' in result

    def test_given_chapters_when_generating_toc_then_creates_linked_list(self):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book"),
            cover=EbookCover(title="Test Cover"),
            sections=[
                EbookSection(
                    type="chapter", title="Chapter 1 — Introduction", content_md="Content 1"
                ),
                EbookSection(
                    type="chapter", title="Chapter 2 — Development", content_md="Content 2"
                ),
            ],
        )
        parser = ContentParser()

        # When
        result = parser.generate_toc_from_structure(structure)

        # Then
        assert '<li class="toc-item toc-level-1">' in result
        assert '<a href="#chapter-1-introduction"' in result
        assert '<a href="#chapter-2-development"' in result
        assert "Chapter 1 — Introduction" in result
        assert "Chapter 2 — Development" in result

    def test_given_toc_disabled_when_generating_toc_then_returns_empty_string(self):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book"),
            cover=EbookCover(title="Test Cover"),
            toc=False,
            sections=[EbookSection(type="chapter", title="Chapter 1", content_md="Content 1")],
        )
        parser = ContentParser()

        # When
        result = parser.generate_toc_from_structure(structure)

        # Then
        assert result == ""

    def test_given_non_chapter_sections_when_generating_toc_then_excludes_them(self):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book"),
            cover=EbookCover(title="Test Cover"),
            sections=[
                EbookSection(type="chapter", title="Chapter 1", content_md="Content 1"),
                EbookSection(type="epilogue", title="Epilogue", content_md="End content"),
                EbookSection(type="chapter", title="Chapter 2", content_md="Content 2"),
            ],
        )
        parser = ContentParser()

        # When
        result = parser.generate_toc_from_structure(structure)

        # Then
        assert "Chapter 1" in result
        assert "Chapter 2" in result
        assert "Epilogue" not in result

    def test_given_markdown_content_when_converting_to_html_then_processes_formatting(self):
        # Given
        structure = EbookStructure(
            meta=EbookMeta(title="Test Book"),
            cover=EbookCover(title="Test Cover"),
            sections=[
                EbookSection(
                    type="chapter",
                    title="Chapter 1",
                    content_md="**Bold text** and *italic text* and `code`",
                )
            ],
        )
        parser = ContentParser()

        # When
        result = parser.generate_html_from_structure(structure)

        # Then
        assert "<strong>Bold text</strong>" in result
        assert "<em>italic text</em>" in result
        assert "<code>code</code>" in result
