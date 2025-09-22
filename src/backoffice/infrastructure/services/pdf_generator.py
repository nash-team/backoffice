import logging
from pathlib import Path

import weasyprint
from jinja2 import Environment, FileSystemLoader

from backoffice.domain.services.content_parser import ContentParser

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    pass


class PDFGenerator:
    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent.parent / "presentation" / "templates"

        self.templates_dir = templates_dir
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir), autoescape=True)
        self.content_parser = ContentParser()
        logger.info(f"PDFGenerator initialized with templates dir: {templates_dir}")

    def generate_pdf_from_json(
        self,
        json_content: str,
        toc_title: str = "Sommaire",
        chapter_numbering: bool = False,
        chapter_numbering_style: str = "arabic",
    ) -> bytes:
        """Generate PDF from structured JSON content"""
        try:
            # Parse la structure JSON
            ebook_structure = self.content_parser.parse_ebook_structure(json_content)

            logger.info(
                f"Generating PDF for '{ebook_structure.meta.title}' "
                f"by {ebook_structure.meta.author}"
            )

            # Générer le contenu HTML à partir de la structure
            processed_content = self.content_parser.generate_html_from_structure(
                ebook_structure,
                chapter_numbering=chapter_numbering,
                chapter_numbering_style=chapter_numbering_style,
            )

            # Générer le TOC
            toc_html = (
                self.content_parser.generate_toc_from_structure(ebook_structure)
                if ebook_structure.toc
                else ""
            )

            template = self.jinja_env.get_template("ebook_base.html")

            html_content = template.render(
                title=ebook_structure.meta.title,
                author=ebook_structure.meta.author,
                processed_content=processed_content,
                toc=ebook_structure.toc,
                toc_title=toc_title,
                toc_html=toc_html,
                chapter_numbering=chapter_numbering,
                chapter_numbering_style=chapter_numbering_style,
            )

            html_doc = weasyprint.HTML(string=html_content)
            pdf_bytes: bytes = html_doc.write_pdf()

            logger.info(
                f"PDF generated successfully for '{ebook_structure.meta.title}', "
                f"size: {len(pdf_bytes)} bytes"
            )
            return pdf_bytes

        except Exception as e:
            logger.error(f"Error generating PDF from JSON: {str(e)}")
            raise PDFGenerationError(f"Failed to generate PDF from JSON: {str(e)}") from e

    def generate_pdf(
        self,
        content: str,
        title: str,
        author: str,
        toc: bool = True,
        toc_title: str = "Sommaire",
        chapter_numbering: bool = False,
        chapter_numbering_style: str = "arabic",
    ) -> bytes:
        try:
            logger.info(f"Generating PDF for '{title}' by {author}")

            chapters = self.content_parser.parse_markdown_content(content)

            processed_content = self.content_parser.generate_html_content(
                chapters,
                chapter_numbering=chapter_numbering,
                chapter_numbering_style=chapter_numbering_style,
            )

            toc_entries = self.content_parser.extract_toc_entries(chapters) if toc else []
            toc_html = self.content_parser.generate_toc_html(toc_entries) if toc else ""

            template = self.jinja_env.get_template("ebook_base.html")

            html_content = template.render(
                title=title,
                author=author,
                processed_content=processed_content,
                toc=toc,
                toc_title=toc_title,
                toc_html=toc_html,
                chapter_numbering=chapter_numbering,
                chapter_numbering_style=chapter_numbering_style,
            )

            html_doc = weasyprint.HTML(string=html_content)
            pdf_bytes: bytes = html_doc.write_pdf()

            logger.info(f"PDF generated successfully for '{title}', size: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Error generating PDF for '{title}': {str(e)}")
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}") from e

    def generate_pdf_from_file(self, html_file_path: Path) -> bytes:
        try:
            html_doc = weasyprint.HTML(filename=str(html_file_path))
            pdf_bytes: bytes = html_doc.write_pdf()
            return pdf_bytes
        except Exception as e:
            logger.error(f"Error generating PDF from file {html_file_path}: {str(e)}")
            raise PDFGenerationError(f"Failed to generate PDF from file: {str(e)}") from e
