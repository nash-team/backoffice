import logging
from pathlib import Path

import weasyprint
from jinja2 import Environment, FileSystemLoader

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.entities.ebook_theme import EbookType, ExtendedEbookConfig
from backoffice.domain.ports.ebook_generator_port import EbookGeneratorPort
from backoffice.domain.services.content_parser import ContentParser
from backoffice.domain.services.cover_generator import CoverGenerationError, CoverGenerator
from backoffice.infrastructure.adapters.modular_pdf_generator_adapter import (
    ModularPDFGeneratorAdapter,
)

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    pass


class PDFGeneratorAdapter(EbookGeneratorPort):
    """PDF generator adapter implementing EbookGeneratorPort"""

    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent.parent / "presentation" / "templates"

        self.templates_dir = templates_dir
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir), autoescape=True)
        self.content_parser = ContentParser()
        self.cover_generator = CoverGenerator(templates_dir)
        # Initialize modular adapter for new ebook types
        self.modular_adapter = ModularPDFGeneratorAdapter()
        logger.info(f"PDFGeneratorAdapter initialized with templates dir: {templates_dir}")

    def supports_format(self, format_type: str) -> bool:
        """Check if this adapter supports the given format"""
        return format_type.lower() == "pdf"

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats"""
        return ["pdf"]

    async def generate_ebook(self, ebook_structure: EbookStructure, config: EbookConfig) -> bytes:
        """Generate PDF from ebook structure and configuration"""

        try:
            if config.format.lower() != "pdf":
                raise PDFGenerationError(f"PDF adapter cannot generate format: {config.format}")

            # Dispatch to modular adapter for extended ebook types
            if isinstance(config, ExtendedEbookConfig):
                logger.info(f"Dispatching to modular adapter for {config.ebook_type.value} ebook")
                return await self._generate_with_modular_adapter(ebook_structure, config)

            logger.info(
                f"Generating PDF for '{ebook_structure.meta.title}' "
                f"by {ebook_structure.meta.author}"
            )

            # Generate cover if enabled
            cover_html = ""
            if config.cover_enabled:
                try:
                    cover_html = self.cover_generator.generate_cover(
                        config=config,
                        ebook_structure=ebook_structure,
                    )
                    logger.info("Cover generated successfully")
                except CoverGenerationError as e:
                    logger.warning(f"Cover generation failed: {e}")
                    cover_html = ""  # Continue without cover

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

            # Combine cover with main content
            full_content = cover_html + processed_content if cover_html else processed_content

            html_content = template.render(
                title=ebook_structure.meta.title,
                author=ebook_structure.meta.author,
                processed_content=full_content,
                toc=config.toc,
                toc_title=config.toc_title,
                toc_html=toc_html,
                chapter_numbering=config.chapter_numbering,
                chapter_numbering_style=config.chapter_numbering_style,
                has_cover=bool(cover_html),
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
    async def generate_pdf_from_json(
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
            pdf_bytes = await self.generate_ebook(ebook_structure, config)
            return pdf_bytes
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

    async def _generate_with_modular_adapter(
        self, ebook_structure: EbookStructure, config: ExtendedEbookConfig
    ) -> bytes:
        """Generate ebook using the modular adapter based on ebook type"""
        try:
            title = ebook_structure.meta.title
            author = ebook_structure.meta.author

            # Extract content based on ebook type
            if config.ebook_type == EbookType.STORY:
                # Extract story chapters from structure
                chapters = []
                for section in ebook_structure.sections or []:
                    chapters.append({"title": section.title, "content": section.content})
                return await self.modular_adapter.generate_story_ebook(
                    title, author, chapters, config
                )

            elif config.ebook_type == EbookType.COLORING:
                # Extract coloring images from structure
                images = []
                for section in ebook_structure.sections or []:
                    # For coloring books, sections might contain image references
                    if hasattr(section, "images") and section.images:
                        for img in section.images:
                            images.append(
                                {
                                    "url": img.get("url", ""),
                                    "title": section.title,
                                    "alt_text": img.get("alt_text", "Image à colorier"),
                                }
                            )
                    else:
                        # Create placeholder coloring page
                        images.append(
                            {
                                "url": "placeholder",  # Replace with actual image generation
                                "title": section.title,
                                "alt_text": (
                                    section.content[:100] + "..."
                                    if len(section.content) > 100
                                    else section.content
                                ),
                            }
                        )
                return await self.modular_adapter.generate_coloring_ebook(
                    title, author, images, config
                )

            elif config.ebook_type == EbookType.MIXED:
                # Extract both stories and images
                chapters = []
                images = []
                for section in ebook_structure.sections or []:
                    # Add as story chapter
                    chapters.append({"title": section.title, "content": section.content})
                    # Add placeholder coloring image
                    images.append(
                        {
                            "url": "placeholder",
                            "title": f"Coloriage - {section.title}",
                            "alt_text": "Image à colorier",
                        }
                    )
                return await self.modular_adapter.generate_mixed_ebook(
                    title, author, chapters, images, config
                )

            else:
                raise PDFGenerationError(f"Unsupported ebook type: {config.ebook_type}")

        except Exception as e:
            logger.error(f"Error in modular ebook generation: {e}")
            raise PDFGenerationError(f"Modular generation failed: {e}") from e
