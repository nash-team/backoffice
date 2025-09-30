import base64
import logging
import os
import tempfile
from pathlib import Path

import weasyprint

from backoffice.domain.constants import PageFormat
from backoffice.domain.entities.page_content import EbookPages
from backoffice.domain.services.pdf_css_generator import PdfCssGenerator
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
        self.css_generator = PdfCssGenerator()
        self.temp_images: set[str] = set()  # Track temporary image files for cleanup

    def generate_pdf_from_pages(
        self, ebook: EbookPages, page_format: PageFormat = PageFormat.A4
    ) -> bytes:
        """
        Generate PDF from modular page structure

        Args:
            ebook: Modular ebook structure

        Returns:
            PDF bytes
        """
        try:
            # Convert data URLs to temporary files for WeasyPrint compatibility
            ebook_with_temp_files = self._convert_data_urls_to_temp_files(ebook)

            # Render entire ebook to HTML
            html_content = self.template_registry.render_ebook(ebook_with_temp_files)

            # Wrap with minimal layout and CSS
            full_html = self._wrap_with_layout(
                html_content, ebook_with_temp_files.meta, page_format
            )

            # Generate PDF with WeasyPrint
            logger.info(f"Starting PDF generation with {len(self.temp_images)} temp images")
            for i, page in enumerate(ebook_with_temp_files.pages):
                logger.info(
                    f"PDF Page {i+1}: type={page.type}, title='{page.title}', "
                    f"template='{page.template}'"
                )
            for temp_file in self.temp_images:
                if os.path.exists(temp_file):
                    file_size = os.path.getsize(temp_file)
                    temp_file_info = (
                        f"Temp file exists before WeasyPrint: {temp_file} ({file_size} bytes)"
                    )
                    logger.info(temp_file_info)
                else:
                    logger.error(f"Temp file missing before WeasyPrint: {temp_file}")

            # Since images use absolute file:/// URIs, no base_url needed
            html_doc = weasyprint.HTML(string=full_html)
            pdf_bytes = html_doc.write_pdf()

            logger.info("PDF generation completed, cleaning up temp files")
            # Clean up temporary image files AFTER PDF generation
            self._cleanup_temp_files()

            if not isinstance(pdf_bytes, bytes):
                raise PdfRenderingError("PDF generation failed: expected bytes, got different type")

            logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Error during PDF generation: {e}")
            # Clean up temporary files even on error
            self._cleanup_temp_files()
            raise PdfRenderingError(f"PDF generation error: {e}") from e

    def _wrap_with_layout(
        self, content: str, meta: dict, page_format: PageFormat = PageFormat.A4
    ) -> str:
        """Wrap content with minimal HTML layout and CSS"""
        title = meta.get("title", "Ebook")

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {self.css_generator.generate_global_css(page_format)}
    </style>
</head>
<body>
{content}
</body>
</html>"""

    def _convert_data_urls_to_temp_files(self, ebook: EbookPages) -> EbookPages:
        """Convert data URLs in ebook pages to temporary file URLs for WeasyPrint compatibility"""
        from copy import deepcopy

        # Create a deep copy to avoid modifying the original
        ebook_copy = deepcopy(ebook)

        for page in ebook_copy.pages:
            if page.type.name == "FULL_PAGE_IMAGE" and page.template == "coloring":
                # Check if page has image_data that needs to be converted to a file
                if "image_data" in page.data and "image_format" in page.data:
                    temp_file_url = self._save_image_data_to_temp_file(
                        page.data["image_data"], page.data["image_format"]
                    )
                    # Replace image_data with image_url pointing to temp file path
                    page.data["image_url"] = temp_file_url
                    # Remove image_data to use the file path instead
                    del page.data["image_data"]
                    logger.info(f"Converted image data to temp file: {temp_file_url}")

                # Also handle existing data URLs that might be too long
                elif "image_url" in page.data and page.data["image_url"].startswith("data:image/"):
                    data_url = page.data["image_url"]
                    # Extract format and data from data URL
                    header, data = data_url.split(",", 1)
                    # Extract format from data:image/format;base64
                    image_format = header.split(";")[0].split("/")[1]

                    temp_file_path = self._save_image_data_to_temp_file(data, image_format)
                    page.data["image_url"] = temp_file_path
                    logger.info(f"Converted data URL to temp file: {temp_file_path}")

        return ebook_copy

    def _save_image_data_to_temp_file(self, image_data: str, image_format: str) -> str:
        """Save base64 image data to a temporary file and return file URL"""
        try:
            # Decode base64 image data
            image_bytes = base64.b64decode(image_data)

            # Create temporary file with appropriate extension
            with tempfile.NamedTemporaryFile(suffix=f".{image_format}", delete=False) as f:
                f.write(image_bytes)
                temp_file_path = f.name

            # Track temp file for cleanup
            self.temp_images.add(temp_file_path)

            # Verify file was created and log details
            if os.path.exists(temp_file_path):
                file_size = os.path.getsize(temp_file_path)
                logger.info(f"Created temp image file: {temp_file_path} ({file_size} bytes)")
            else:
                logger.error(f"Temp file was not created: {temp_file_path}")

            # Return proper file URI using Path for cross-platform compatibility
            return Path(temp_file_path).resolve().as_uri()

        except Exception as e:
            logger.error(f"Failed to save image data to temp file: {e}")
            # Fallback to data URL if temp file creation fails
            return f"data:image/{image_format};base64,{image_data}"

    def _cleanup_temp_files(self):
        """Clean up temporary image files"""
        logger.info(f"Cleaning up {len(self.temp_images)} temp files")
        for temp_file in self.temp_images:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.info(f"Deleted temp file: {temp_file}")
                else:
                    logger.warning(f"Temp file already missing: {temp_file}")
            except Exception as e:
                logger.error(f"Failed to clean up temp file {temp_file}: {e}")

        self.temp_images.clear()
        logger.info("Temp file cleanup completed")
