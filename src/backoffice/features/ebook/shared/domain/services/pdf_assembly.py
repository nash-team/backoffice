"""PDF assembly service (V1 slim - interface only)."""

import logging

from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage, AssemblyPort

logger = logging.getLogger(__name__)


class PDFAssemblyService:
    """Service for assembling pages into PDF (V1 slim).

    This is a thin wrapper around the AssemblyPort.
    The real implementation (WeasyPrint) lives in infrastructure.
    """

    def __init__(self, assembly_port: AssemblyPort):
        """Initialize PDF assembly service.

        Args:
            assembly_port: Port for PDF assembly
        """
        self.assembly_port = assembly_port

    async def assemble_ebook(
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
        total_pages = 1 + len(pages)  # cover + content
        logger.info(f"📄 Assembling PDF: 1 cover + {len(pages)} pages = {total_pages} total")

        pdf_uri = await self.assembly_port.assemble_pdf(
            cover=cover,
            pages=pages,
            output_path=output_path,
        )

        logger.info(f"✅ PDF assembled: {pdf_uri}")
        return pdf_uri
