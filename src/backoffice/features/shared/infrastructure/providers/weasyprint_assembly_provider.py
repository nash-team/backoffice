"""WeasyPrint provider for PDF assembly."""

import logging
from pathlib import Path

from weasyprint import HTML

from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.shared.domain.ports.assembly_port import AssembledPage, AssemblyPort

logger = logging.getLogger(__name__)


class WeasyPrintAssemblyProvider(AssemblyPort):
    """WeasyPrint provider for PDF assembly (V1 slim).

    V1 simplification:
    - Simple HTML template with cover + content pages
    - Full-bleed images (no borders)
    - No TOC or page numbering
    """

    async def assemble_pdf(
        self,
        cover: AssembledPage,
        pages: list[AssembledPage],
        output_path: str,
    ) -> str:
        """Assemble cover and content pages into a PDF.

        Args:
            cover: Cover page to include
            pages: Content pages to include
            output_path: Path where PDF should be saved

        Returns:
            URI to the generated PDF

        Raises:
            DomainError: If assembly fails
        """
        try:
            logger.info(f"Assembling PDF: 1 cover + {len(pages)} pages")

            # Build HTML with embedded images
            html_content = self._build_html(cover, pages)

            # Generate PDF using WeasyPrint
            logger.info(f"Rendering PDF to: {output_path}")
            HTML(string=html_content).write_pdf(output_path)

            # Verify output
            output_file = Path(output_path)
            if not output_file.exists():
                raise DomainError(
                    code=ErrorCode.IMAGE_TOO_SMALL,
                    message="PDF assembly failed: output file not created",
                    actionable_hint="Check WeasyPrint logs for errors",
                    context={"output_path": output_path},
                )

            file_size = output_file.stat().st_size
            logger.info(f"✅ PDF assembled: {output_path} ({file_size} bytes)")

            return f"file://{output_path}"

        except Exception as e:
            logger.error(f"❌ PDF assembly failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.IMAGE_TOO_SMALL,
                message=f"PDF assembly failed: {str(e)}",
                actionable_hint="Check image data and WeasyPrint installation",
                context={"output_path": output_path, "error": str(e)},
            ) from e

    def _build_html(self, cover: AssembledPage, pages: list[AssembledPage]) -> str:
        """Build HTML content with embedded images.

        Args:
            cover: Cover page
            pages: Content pages

        Returns:
            HTML string
        """
        # Convert images to base64 for embedding
        cover_data_uri = self._image_to_data_uri(cover.image_data, cover.image_format)
        page_data_uris = [
            self._image_to_data_uri(page.image_data, page.image_format) for page in pages
        ]

        # Build HTML - Square format for coloring books
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {
                    size: 21cm 21cm;
                    margin: 0;
                }
                body {
                    margin: 0;
                    padding: 0;
                }
                .page {
                    page-break-after: always;
                    width: 21cm;
                    height: 21cm;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                }
                .page:last-child {
                    page-break-after: auto;
                }
                .page img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
            </style>
        </head>
        <body>
        """

        # Add cover
        html += f"""
            <div class="page cover">
                <img src="{cover_data_uri}" alt="{cover.title}">
            </div>
        """

        # Add content pages
        for page, data_uri in zip(pages, page_data_uris, strict=False):
            html += f"""
            <div class="page content">
                <img src="{data_uri}" alt="{page.title}">
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    def _image_to_data_uri(self, image_data: bytes, image_format: str) -> str:
        """Convert image bytes to data URI.

        Args:
            image_data: Image bytes
            image_format: Image format (PNG, SVG, etc.)

        Returns:
            Data URI string
        """
        import base64

        if image_format.upper() == "SVG":
            # SVG can be embedded as text
            svg_content = image_data.decode("utf-8")
            encoded = base64.b64encode(svg_content.encode()).decode()
            return f"data:image/svg+xml;base64,{encoded}"
        else:
            # Raster images (PNG, JPEG, etc.)
            encoded = base64.b64encode(image_data).decode()
            mime_type = f"image/{image_format.lower()}"
            return f"data:{mime_type};base64,{encoded}"
