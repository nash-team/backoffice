from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backoffice.domain.entities.page_content import EbookPages
from backoffice.domain.services.pdf_renderer import PdfRenderer, PdfRenderingError


class TestPdfRenderer:
    """Test suite for PdfRenderer using London methodology"""

    def setup_method(self):
        """Set up test fixtures"""
        self.templates_dir = Path("/fake/templates")
        self.renderer = PdfRenderer(self.templates_dir)

    @patch("backoffice.domain.services.pdf_renderer.weasyprint.HTML")
    @patch("backoffice.domain.services.pdf_renderer.TemplateRegistry")
    def test_generate_pdf_from_pages_success(self, mock_template_registry, mock_html):
        # Given
        ebook = EbookPages(meta={"title": "Test Ebook", "author": "Test Author"}, pages=[])
        expected_pdf_bytes = b"fake pdf content"

        # Mock template registry
        mock_registry_instance = Mock()
        mock_template_registry.return_value = mock_registry_instance
        mock_registry_instance.render_ebook.return_value = "<div>Rendered HTML</div>"

        # Mock weasyprint
        mock_html_doc = Mock()
        mock_html.return_value = mock_html_doc
        mock_html_doc.write_pdf.return_value = expected_pdf_bytes

        # When
        result = self.renderer.generate_pdf_from_pages(ebook)

        # Then
        assert result == expected_pdf_bytes
        mock_registry_instance.render_ebook.assert_called_once_with(ebook)
        mock_html.assert_called_once()
        mock_html_doc.write_pdf.assert_called_once()

    @patch("backoffice.domain.services.pdf_renderer.weasyprint.HTML")
    @patch("backoffice.domain.services.pdf_renderer.TemplateRegistry")
    def test_generate_pdf_from_pages_invalid_return_type(self, mock_template_registry, mock_html):
        # Given
        ebook = EbookPages(meta={"title": "Test Ebook"}, pages=[])

        # Mock template registry
        mock_registry_instance = Mock()
        mock_template_registry.return_value = mock_registry_instance
        mock_registry_instance.render_ebook.return_value = "<div>Rendered HTML</div>"

        # Mock weasyprint to return non-bytes
        mock_html_doc = Mock()
        mock_html.return_value = mock_html_doc
        mock_html_doc.write_pdf.return_value = "not bytes"

        # When/Then
        with pytest.raises(PdfRenderingError) as exc_info:
            self.renderer.generate_pdf_from_pages(ebook)

        assert "expected bytes, got different type" in str(exc_info.value)

    @patch("backoffice.domain.services.pdf_renderer.weasyprint.HTML")
    @patch("backoffice.domain.services.pdf_renderer.TemplateRegistry")
    def test_generate_pdf_from_pages_template_error(self, mock_template_registry, mock_html):
        # Given
        ebook = EbookPages(meta={"title": "Test Ebook"}, pages=[])

        # Mock template registry to raise exception
        mock_registry_instance = Mock()
        mock_template_registry.return_value = mock_registry_instance
        mock_registry_instance.render_ebook.side_effect = Exception("Template error")

        # When/Then
        with pytest.raises(PdfRenderingError) as exc_info:
            self.renderer.generate_pdf_from_pages(ebook)

        assert "PDF generation error" in str(exc_info.value)
        assert "Template error" in str(exc_info.value)

    @patch("backoffice.domain.services.pdf_renderer.weasyprint.HTML")
    @patch("backoffice.domain.services.pdf_renderer.TemplateRegistry")
    def test_generate_pdf_from_pages_weasyprint_error(self, mock_template_registry, mock_html):
        # Given
        ebook = EbookPages(meta={"title": "Test Ebook"}, pages=[])

        # Mock template registry
        mock_registry_instance = Mock()
        mock_template_registry.return_value = mock_registry_instance
        mock_registry_instance.render_ebook.return_value = "<div>Rendered HTML</div>"

        # Mock weasyprint to raise exception
        mock_html.side_effect = Exception("WeasyPrint error")

        # When/Then
        with pytest.raises(PdfRenderingError) as exc_info:
            self.renderer.generate_pdf_from_pages(ebook)

        assert "PDF generation error" in str(exc_info.value)
        assert "WeasyPrint error" in str(exc_info.value)

    def test_wrap_with_layout_includes_title(self):
        # Given
        content = "<div>Test content</div>"
        meta = {"title": "Test Title"}

        # When
        result = self.renderer._wrap_with_layout(content, meta)

        # Then
        assert "<title>Test Title</title>" in result
        assert content in result
        assert "<!DOCTYPE html>" in result
        assert '<html lang="fr">' in result

    def test_wrap_with_layout_default_title(self):
        # Given
        content = "<div>Test content</div>"
        meta = {}

        # When
        result = self.renderer._wrap_with_layout(content, meta)

        # Then
        assert "<title>Ebook</title>" in result

    def test_wrap_with_layout_includes_css(self):
        # Given
        content = "<div>Test content</div>"
        meta = {"title": "Test"}

        # When
        result = self.renderer._wrap_with_layout(content, meta)

        # Then
        assert "<style>" in result
        assert "@page {" in result
        assert "font-family:" in result

    def test_get_global_css_includes_page_types(self):
        # When
        css = self.renderer._get_global_css()

        # Then
        assert "@page cover {" in css
        assert "@page full-bleed {" in css
        assert "@page minimal {" in css
        assert ".page.cover { page: cover; }" in css

    def test_get_global_css_includes_page_breaks(self):
        # When
        css = self.renderer._get_global_css()

        # Then
        assert ".page-break-before { page-break-before: always; }" in css
        assert ".page-break-after { page-break-after: always; }" in css

    def test_get_global_css_includes_image_styles(self):
        # When
        css = self.renderer._get_global_css()

        # Then
        assert "img { max-width: 100%; height: auto; }" in css
        assert ".full-page-image {" in css
        assert "width: 100vw;" in css

    @patch("backoffice.domain.services.pdf_renderer.TemplateRegistry")
    def test_init_creates_template_registry(self, mock_template_registry):
        # Given
        templates_dir = "/test/templates"

        # When
        renderer = PdfRenderer(templates_dir)

        # Then
        mock_template_registry.assert_called_once_with(templates_dir)
        assert renderer.templates_dir == Path(templates_dir)

    @patch("backoffice.domain.services.pdf_renderer.TemplateRegistry")
    def test_init_with_path_object(self, mock_template_registry):
        # Given
        templates_dir = Path("/test/templates")

        # When
        renderer = PdfRenderer(templates_dir)

        # Then
        mock_template_registry.assert_called_once_with(templates_dir)
        assert renderer.templates_dir == templates_dir
