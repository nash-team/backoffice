import base64
import logging
from io import BytesIO
from pathlib import Path

import weasyprint
from jinja2 import Environment, FileSystemLoader
from PIL import Image

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.entities.ebook_theme import EbookType, ExtendedEbookConfig
from backoffice.domain.entities.image_page import ColoringPageRequest
from backoffice.domain.ports.ebook_generator_port import EbookGeneratorPort
from backoffice.domain.services.content_parser import ContentParser
from backoffice.domain.services.cover_generator import CoverGenerationError, CoverGenerator
from backoffice.domain.usecases.generate_coloring_pages import GenerateColoringPagesUseCase
from backoffice.infrastructure.adapters.modular_pdf_generator_adapter import (
    ModularPDFGeneratorAdapter,
)
from backoffice.infrastructure.adapters.openai_image_generator import OpenAIImageGenerator
from backoffice.infrastructure.adapters.potrace_vectorizer import PotraceVectorizer

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

        # Initialize image generation services
        self.image_generator = OpenAIImageGenerator()
        self.vectorizer = PotraceVectorizer()
        self.coloring_pages_use_case = GenerateColoringPagesUseCase(
            self.image_generator, self.vectorizer
        )

        logger.info(f"PDFGeneratorAdapter initialized with templates dir: {templates_dir}")
        logger.info(f"Image generator available: {self.image_generator.is_available()}")
        logger.info(f"Vectorizer available: {self.vectorizer.is_available()}")

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
                # Generate real coloring images from AI
                logger.info("Generating coloring pages with AI images...")

                # Create requests for each section
                coloring_requests = []
                for section in ebook_structure.sections or []:
                    # For coloring books, sections might contain image references
                    if hasattr(section, "images") and section.images:
                        # Use existing images if available
                        for img in section.images:
                            if img.get("url") and img["url"] != "placeholder":
                                # Use existing image URL
                                continue

                    # Generate AI image from section content
                    coloring_requests.append(
                        ColoringPageRequest(
                            description=section.content,
                            title=section.title,
                            generate_from_ai=True,
                        )
                    )

                # Generate cover image first (separate from coloring pages)
                cover_image_data_url = None
                if coloring_requests:
                    try:
                        # Generate a special cover image with a more general/appealing description
                        first_section = (
                            ebook_structure.sections[0] if ebook_structure.sections else None
                        )
                        if first_section:
                            cover_prompt = (
                                f"Couverture de livre de coloriage: {first_section.content}. "
                                "Style simple et attrayant pour enfants."
                            )
                            logger.info(
                                f"Generating cover image with prompt: {cover_prompt[:100]}..."
                            )

                            cover_request = [
                                ColoringPageRequest(
                                    description=cover_prompt,
                                    title=f"Couverture - {ebook_structure.meta.title}",
                                    generate_from_ai=True,
                                )
                            ]

                            cover_pages = await self.coloring_pages_use_case.execute(
                                cover_request, convert_to_svg=False
                            )

                            if cover_pages and cover_pages[0].image_data:
                                # Optimize and create data URL for cover
                                optimized_cover = self._optimize_image_for_pdf(
                                    cover_pages[0].image_data
                                )
                                cover_image_base64 = base64.b64encode(optimized_cover).decode(
                                    "utf-8"
                                )
                                cover_image_data_url = (
                                    f"data:image/jpeg;base64,{cover_image_base64}"
                                )
                                logger.info(
                                    f"Generated cover image: {len(cover_image_data_url)} chars"
                                )

                    except Exception as e:
                        logger.error(f"Error generating cover image: {e}")
                        cover_image_data_url = None

                # Generate the coloring pages with AI
                if coloring_requests:
                    try:
                        logger.info(f"Generating {len(coloring_requests)} AI coloring pages")
                        image_pages = await self.coloring_pages_use_case.execute(
                            coloring_requests,
                            convert_to_svg=False,  # Use PNG for PDF embedding
                        )

                        # Convert ImagePage objects to the format expected by modular adapter
                        images = []
                        for page in image_pages:
                            # Debug: check image data
                            data_size = len(page.image_data) if page.image_data else "None"
                            logger.debug(
                                f"Processing ImagePage: title={page.title}, "
                                f"format={page.image_format}, data_size={data_size}"
                            )

                            if not page.image_data:
                                logger.warning(f"No image data for page: {page.title}")
                                continue

                            # Optimize and embed image data as base64
                            try:
                                # Optimize image size for PDF embedding
                                optimized_image_data = self._optimize_image_for_pdf(page.image_data)
                                image_base64 = base64.b64encode(optimized_image_data).decode(
                                    "utf-8"
                                )

                                # Use JPEG format since we optimize to JPEG
                                data_url = f"data:image/jpeg;base64,{image_base64}"

                                url_len = len(data_url)
                                logger.info(
                                    f"Created optimized data URL for {page.title}: "
                                    f"{url_len} chars (format: jpeg)"
                                )

                                images.append(
                                    {
                                        "url": data_url,
                                        "title": page.title,
                                        "alt_text": page.description
                                        or "Image à colorier générée par IA",
                                    }
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error encoding image for page {page.title}: {str(e)}"
                                )
                                continue

                        logger.info(f"Successfully generated {len(images)} AI coloring images")

                    except Exception as e:
                        logger.error(
                            f"Error generating AI images, falling back to placeholders: {e}"
                        )
                        # Fallback to placeholders if AI generation fails
                        images = []
                        for section in ebook_structure.sections or []:
                            images.append(
                                {
                                    "url": "placeholder",
                                    "title": section.title,
                                    "alt_text": (
                                        section.content[:100] + "..."
                                        if len(section.content) > 100
                                        else section.content
                                    ),
                                }
                            )
                else:
                    # No sections to process, use placeholders
                    images = [
                        {
                            "url": "placeholder",
                            "title": "Image de coloriage",
                            "alt_text": "Image à colorier",
                        }
                    ]

                return await self.modular_adapter.generate_coloring_ebook(
                    title, author, images, config, cover_image_data_url
                )

            elif config.ebook_type == EbookType.MIXED:
                # Extract both stories and generate AI images
                logger.info("Generating mixed ebook with AI coloring images...")

                chapters = []
                coloring_requests = []

                for section in ebook_structure.sections or []:
                    # Add as story chapter
                    chapters.append({"title": section.title, "content": section.content})

                    # Generate AI coloring image for this section
                    coloring_requests.append(
                        ColoringPageRequest(
                            description=section.content,
                            title=f"Coloriage - {section.title}",
                            generate_from_ai=True,
                        )
                    )

                # Generate the coloring images with AI
                images = []
                if coloring_requests:
                    try:
                        logger.info(
                            f"Generating {len(coloring_requests)} AI coloring images for mixed"
                        )
                        image_pages = await self.coloring_pages_use_case.execute(
                            coloring_requests, convert_to_svg=False
                        )

                        for page in image_pages:
                            # Optimize and embed image data as base64
                            optimized_image_data = self._optimize_image_for_pdf(page.image_data)
                            image_base64 = base64.b64encode(optimized_image_data).decode("utf-8")
                            data_url = f"data:image/jpeg;base64,{image_base64}"

                            images.append(
                                {
                                    "url": data_url,
                                    "title": page.title,
                                    "alt_text": page.description
                                    or "Image à colorier générée par IA",
                                }
                            )

                        logger.info(
                            f"Successfully generated {len(images)} AI images for mixed ebook"
                        )

                    except Exception as e:
                        logger.error(
                            f"Error generating AI images for mixed ebook, using placeholders: {e}"
                        )
                        # Fallback to placeholders
                        for section in ebook_structure.sections or []:
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

    def _optimize_image_for_pdf(
        self, image_data: bytes, max_size: tuple[int, int] = (800, 600), quality: int = 85
    ) -> bytes:
        """
        Optimize image for PDF embedding by resizing and compressing

        Args:
            image_data: Original image bytes
            max_size: Maximum size (width, height) for the image
            quality: JPEG quality (1-100)

        Returns:
            Optimized image bytes
        """
        try:
            # Open image from bytes
            img = Image.open(BytesIO(image_data))

            # Convert RGBA to RGB if necessary (for JPEG compatibility)
            if img.mode == "RGBA":
                # Create a white background
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                img = rgb_img
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if too large
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save as optimized JPEG
            output = BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            optimized_data = output.getvalue()

            original_size = len(image_data)
            optimized_size = len(optimized_data)
            percentage = optimized_size / original_size * 100
            logger.info(
                f"Image optimized: {original_size} -> {optimized_size} bytes ({percentage:.1f}%)"
            )

            return optimized_data

        except Exception as e:
            logger.warning(f"Failed to optimize image: {str(e)}, using original")
            return image_data
