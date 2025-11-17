"""Shared regeneration service with common validation and PDF rebuild logic."""

import base64
import logging
import tempfile
from pathlib import Path

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.file_storage_port import FileStoragePort
from backoffice.features.ebook.shared.domain.services.pdf_assembly import PDFAssemblyService

logger = logging.getLogger(__name__)


class RegenerationService:
    """Base service for ebook regeneration operations.

    Provides common validation and PDF rebuild logic shared across all
    regeneration use cases (cover, content page, back cover).
    """

    def __init__(
        self,
        assembly_service: PDFAssemblyService,
        file_storage: FileStoragePort,
    ):
        """Initialize regeneration service.

        Args:
            assembly_service: Service for PDF assembly
            file_storage: Service for file storage (Google Drive)
        """
        self.assembly_service = assembly_service
        self.file_storage = file_storage

    def validate_ebook_for_regeneration(self, ebook: Ebook) -> None:
        """Validate that ebook can be regenerated.

        Business rules:
        - Only DRAFT ebooks can be modified
        - Ebook must have structure_json with pages metadata

        Args:
            ebook: Ebook to validate

        Raises:
            ValueError: If ebook cannot be regenerated
        """
        # Business rule: only DRAFT ebooks can be modified
        if ebook.status != EbookStatus.DRAFT:
            raise ValueError(
                f"Cannot regenerate for ebook with status {ebook.status.value}. "
                f"Only DRAFT ebooks can be modified."
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise ValueError(
                "Cannot regenerate: ebook structure is missing. "
                "Please regenerate the entire ebook instead."
            )

    async def rebuild_and_upload_pdf(
        self,
        ebook: Ebook,
        assembled_pages: list[AssembledPage],
        ebook_repository,
        filename_suffix: str = "regenerated",
    ) -> tuple[Path, str | None]:
        """Rebuild PDF from assembled pages and upload to storage.

        This method:
        1. Assembles pages into PDF
        2. Saves PDF bytes to database (for preview endpoint)
        3. Uploads to file storage if available (Google Drive or local)
        4. Returns PDF path and preview URL

        Args:
            ebook: Ebook being regenerated
            assembled_pages: List of assembled pages (cover first, then content)
            ebook_repository: Repository for saving PDF bytes to database
            filename_suffix: Suffix for PDF filename (e.g., "regenerated", "page1_regenerated")

        Returns:
            Tuple of (PDF path, preview URL)

        Raises:
            Exception: If PDF assembly fails
        """
        # Split into cover and content pages
        cover_page = assembled_pages[0]
        content_pages = assembled_pages[1:] if len(assembled_pages) > 1 else []

        # Generate PDF in temp directory
        pdf_path = Path(tempfile.gettempdir()) / f"ebook_{ebook.id}_{filename_suffix}.pdf"

        logger.info(f"📄 Assembling PDF: {pdf_path}")
        await self.assembly_service.assemble_ebook(
            cover=cover_page,
            pages=content_pages,
            output_path=str(pdf_path),
        )

        logger.info(f"✅ PDF assembled: {pdf_path}")

        # Save PDF bytes to database (ALWAYS - for /api/ebooks/{id}/pdf endpoint)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        await ebook_repository.save_ebook_bytes(ebook.id, pdf_bytes)
        logger.info(f"💾 PDF bytes saved to database ({len(pdf_bytes)} bytes)")

        # Upload to file storage (optional - only if available)
        preview_url = await self._upload_pdf_to_storage(
            ebook=ebook,
            pdf_path=pdf_path,
            pdf_bytes=pdf_bytes,
            filename_suffix=filename_suffix,
        )

        return pdf_path, preview_url

    async def _upload_pdf_to_storage(
        self,
        ebook: Ebook,
        pdf_path: Path,
        pdf_bytes: bytes,
        filename_suffix: str,
    ) -> str | None:
        """Upload PDF to storage (Google Drive or local).

        Args:
            ebook: Ebook being uploaded
            pdf_path: Path to PDF file (for fallback URL)
            pdf_bytes: PDF bytes to upload
            filename_suffix: Suffix for filename

        Returns:
            Preview URL (Drive URL or local file:// URL), or None if storage unavailable
        """
        if not self.file_storage.is_available():
            logger.info("ℹ️ File storage not available, PDF stored in database only")
            return None

        try:
            filename = f"{ebook.title or 'coloring_book'}_{filename_suffix}.pdf"
            upload_result = await self.file_storage.upload_ebook(
                file_bytes=pdf_bytes,
                filename=filename,
                metadata={
                    "title": ebook.title or "Untitled",
                    "author": ebook.author or "Unknown",
                    "ebook_id": str(ebook.id),
                    "regenerated": "true",
                },
            )

            # Update ebook with new Drive info
            ebook.drive_id = upload_result.get("storage_id")
            preview_url = upload_result.get("storage_url")

            logger.info(f"☁️ Uploaded to file storage: {ebook.drive_id}")
            return preview_url

        except Exception as e:
            logger.warning(f"⚠️ Failed to upload to file storage: {e}")
            # No fallback needed - PDF is already in database
            return None

    def assemble_pages_from_structure(
        self,
        pages_meta: list[dict],
    ) -> list[AssembledPage]:
        """Convert structure_json pages metadata to AssembledPage objects.

        Args:
            pages_meta: List of page metadata from structure_json

        Returns:
            List of AssembledPage objects ready for PDF assembly
        """
        assembled_pages = []

        for page_meta in pages_meta:
            page_data = base64.b64decode(page_meta["image_data_base64"])
            assembled_pages.append(
                AssembledPage(
                    page_number=page_meta["page_number"],
                    title=page_meta.get("title", f"Page {page_meta['page_number']}"),
                    image_data=page_data,
                    image_format=page_meta.get("image_format", "PNG"),
                )
            )

        return assembled_pages

    def update_page_in_structure(
        self,
        pages_meta: list[dict],
        page_number: int,
        new_image_data: bytes,
        title: str | None = None,
    ) -> list[dict]:
        """Update a single page in structure_json pages metadata.

        Args:
            pages_meta: Original pages metadata
            page_number: Page number to update (0-based)
            new_image_data: New image bytes
            title: Optional new title (defaults to "Page {page_number}" or "Cover")

        Returns:
            Updated pages metadata
        """
        updated_pages_meta = pages_meta.copy()

        # Determine title
        if title is None:
            title = "Cover" if page_number == 0 else f"Page {page_number}"

        # Update the specific page
        updated_pages_meta[page_number] = {
            "page_number": page_number,
            "title": title,
            "image_format": "PNG",
            "image_data_base64": base64.b64encode(new_image_data).decode(),
        }

        return updated_pages_meta
