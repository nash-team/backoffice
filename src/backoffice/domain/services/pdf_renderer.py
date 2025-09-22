import logging
from pathlib import Path

import weasyprint

from backoffice.domain.entities.page_content import EbookPages
from backoffice.domain.services.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)


class PdfRenderingError(Exception):
    """Exception raised when PDF rendering fails"""

    pass


class PdfRenderer:
    """Renders ebook pages to PDF format"""

    def __init__(self, templates_dir: str | Path):
        """Initialize with templates directory"""
        self.templates_dir = Path(templates_dir)
        self.template_registry = TemplateRegistry(templates_dir)

    def generate_pdf_from_pages(self, ebook: EbookPages) -> bytes:
        """
        Generate PDF from modular page structure

        Args:
            ebook: Modular ebook structure

        Returns:
            PDF bytes
        """
        try:
            # Render entire ebook to HTML
            html_content = self.template_registry.render_ebook(ebook)

            # Wrap with minimal layout and CSS
            full_html = self._wrap_with_layout(html_content, ebook.meta)

            # Generate PDF with WeasyPrint
            html_doc = weasyprint.HTML(string=full_html)
            pdf_bytes = html_doc.write_pdf()

            if not isinstance(pdf_bytes, bytes):
                raise PdfRenderingError("PDF generation failed: expected bytes, got different type")

            logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Error during PDF generation: {e}")
            raise PdfRenderingError(f"PDF generation error: {e}") from e

    def _wrap_with_layout(self, content: str, meta: dict) -> str:
        """Wrap content with minimal HTML layout and CSS"""
        title = meta.get("title", "Ebook")

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {self._get_global_css()}
    </style>
</head>
<body>
{content}
</body>
</html>"""

    def _get_global_css(self) -> str:
        """Get global CSS styles for PDF rendering"""
        return """
        /* Global CSS for all page types */
        @page {
            size: A4;
            margin: 2cm;
        }

        /* Cover pages */
        @page cover {
            size: A4;
            margin: 0;
        }

        /* Full page bleed (coloring) */
        @page full-bleed {
            size: A4;
            margin: 0;
        }

        /* Standard pages with reduced margins */
        @page minimal {
            size: A4;
            margin: 1cm;
        }

        body {
            font-family: "Georgia", "Times New Roman", serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }

        /* Apply CSS layouts */
        .page.cover { page: cover; }
        .page.full-bleed { page: full-bleed; }
        .page.minimal { page: minimal; }
        .page.standard { page: auto; }

        /* Page breaks */
        .page-break-before { page-break-before: always; }
        .page-break-after { page-break-after: always; }

        /* Generic styles */
        h1, h2, h3 { page-break-after: avoid; }
        img { max-width: 100%; height: auto; }

        /* Full page image style */
        .full-page-image {
            width: 100vw;
            height: 100vh;
            object-fit: cover;
            page-break-before: always;
        }
        """
