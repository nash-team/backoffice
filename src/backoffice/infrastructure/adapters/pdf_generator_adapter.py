import logging
from pathlib import Path

import weasyprint
from jinja2 import Environment, FileSystemLoader

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.ports.ebook_generator_port import EbookGeneratorPort
from backoffice.domain.services.content_parser import ContentParser

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    pass


class PDFGeneratorAdapter(EbookGeneratorPort):
    """PDF generator adapter implementing EbookGeneratorPort"""

    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates"

        self.templates_dir = templates_dir
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir), autoescape=True)
        self.content_parser = ContentParser()
        logger.info(f"PDFGeneratorAdapter initialized with templates dir: {templates_dir}")

    def supports_format(self, format_type: str) -> bool:
        """Check if this adapter supports the given format"""
        return format_type.lower() == "pdf"

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats"""
        return ["pdf"]

    def generate_ebook(self, ebook_structure: EbookStructure, config: EbookConfig) -> bytes:
        """Generate PDF from ebook structure and configuration"""
        try:
            if config.format.lower() != "pdf":
                raise PDFGenerationError(f"PDF adapter cannot generate format: {config.format}")

            logger.info(
                f"Generating PDF for '{ebook_structure.meta.title}' "
                f"by {ebook_structure.meta.author}"
            )

            # Generate HTML content from structure
            processed_content = self.content_parser.generate_html_from_structure(
                ebook_structure,
                chapter_numbering=config.chapter_numbering,
                chapter_numbering_style=config.chapter_numbering_style,
            )

            # Generate TOC
            toc_html = (
                self.content_parser.generate_toc_from_structure(ebook_structure)
                if config.toc
                else ""
            )

            template = self.jinja_env.get_template("ebook_base.html")

            html_content = template.render(
                title=ebook_structure.meta.title,
                author=ebook_structure.meta.author,
                processed_content=processed_content,
                toc=config.toc,
                toc_title=config.toc_title,
                toc_html=toc_html,
                chapter_numbering=config.chapter_numbering,
                chapter_numbering_style=config.chapter_numbering_style,
            )

            html_doc = weasyprint.HTML(string=html_content)
            pdf_bytes: bytes = html_doc.write_pdf()

            logger.info(
                f"PDF generated successfully for '{ebook_structure.meta.title}', "
                f"size: {len(pdf_bytes)} bytes"
            )
            return pdf_bytes

        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}") from e

    # Legacy methods for backward compatibility
    def generate_pdf_from_json(
        self,
        json_content: str,
        toc_title: str = "Sommaire",
        chapter_numbering: bool = False,
        chapter_numbering_style: str = "arabic",
    ) -> bytes:
        """Legacy method - parse JSON and generate PDF"""
        try:
            ebook_structure = self.content_parser.parse_ebook_structure(json_content)
            config = EbookConfig(
                toc_title=toc_title,
                chapter_numbering=chapter_numbering,
                chapter_numbering_style=chapter_numbering_style,
                format="pdf",
            )
            return self.generate_ebook(ebook_structure, config)
        except Exception as e:
            logger.error(f"Error in legacy PDF generation: {str(e)}")
            raise PDFGenerationError(f"Failed to generate PDF from JSON: {str(e)}") from e

    def generate_pdf_from_file(self, html_file_path: Path) -> bytes:
        """Generate PDF directly from HTML file"""
        try:
            html_doc = weasyprint.HTML(filename=str(html_file_path))
            pdf_bytes: bytes = html_doc.write_pdf()
            return pdf_bytes
        except Exception as e:
            logger.error(f"Error generating PDF from file {html_file_path}: {str(e)}")
            raise PDFGenerationError(f"Failed to generate PDF from file: {str(e)}") from e
