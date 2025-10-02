"""Use case for regenerating ebook back cover only."""

import base64
import logging
from pathlib import Path

from backoffice.domain.cover_generation import CoverGenerationService
from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.pdf_assembly import PDFAssemblyService
from backoffice.domain.ports.assembly_port import AssembledPage
from backoffice.domain.ports.ebook.ebook_port import EbookPort
from backoffice.domain.ports.file_storage_port import FileStoragePort
from backoffice.infrastructure.utils.color_utils import extract_dominant_color_exact

logger = logging.getLogger(__name__)


class RegenerateBackCoverUseCase:
    """Regenerate the back cover of a coloring book ebook.

    This regenerates ONLY the back cover while keeping:
    - Front cover (extracts color from it)
    - All content pages
    - Same theme and metadata
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        cover_service: CoverGenerationService,
        assembly_service: PDFAssemblyService,
        file_storage: FileStoragePort,
    ):
        """Initialize regenerate back cover use case.

        Args:
            ebook_repository: Repository for ebook persistence
            cover_service: Service for cover generation
            assembly_service: Service for PDF assembly
            file_storage: Service for file storage (Google Drive)
        """
        self.ebook_repository = ebook_repository
        self.cover_service = cover_service
        self.assembly_service = assembly_service
        self.file_storage = file_storage

    async def execute(
        self,
        ebook_id: int,
        prompt_override: str | None = None,
    ) -> Ebook:
        """Regenerate the back cover of an ebook.

        Args:
            ebook_id: ID of the ebook
            prompt_override: Optional custom prompt for back cover generation

        Returns:
            Updated ebook with new back cover

        Raises:
            ValueError: If ebook not found or not in PENDING status
        """
        # Retrieve the ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise ValueError(f"Ebook with id {ebook_id} not found")

        # Business rule: only DRAFT ebooks can be modified
        if ebook.status != EbookStatus.DRAFT:
            raise ValueError(
                f"Cannot regenerate back cover for ebook with status {ebook.status.value}. "
                f"Only DRAFT ebooks can be modified."
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise ValueError(
                "Cannot regenerate back cover: ebook structure is missing. "
                "Please regenerate the entire ebook instead."
            )

        pages_meta = ebook.structure_json["pages_meta"]
        if len(pages_meta) < 2:
            raise ValueError(
                "Cannot regenerate back cover: ebook must have at least 2 pages (cover + back)"
            )

        logger.info(f"🔄 Regenerating BACK COVER for ebook {ebook_id}: {ebook.title}")

        # Step 1: Extract front cover bytes (first page)
        front_cover_meta = pages_meta[0]
        front_cover_bytes = base64.b64decode(front_cover_meta["image_data_base64"])

        # Step 2: Remove text from cover to create back cover with Gemini Vision
        logger.info("🍌 Creating back cover (same image without text)...")

        back_cover_data = await self.cover_service.cover_port.convert_cover_to_line_art_with_gemini(
            cover_bytes=front_cover_bytes
        )

        logger.info(f"✅ Back cover regenerated via Gemini: {len(back_cover_data)} bytes")

        # Step 4: Rebuild PDF with new back cover
        assembled_pages = []

        # Add all pages EXCEPT the last one (old back cover)
        for _i, page_meta in enumerate(pages_meta[:-1]):
            page_data = base64.b64decode(page_meta["image_data_base64"])
            assembled_pages.append(
                AssembledPage(
                    page_number=page_meta["page_number"],
                    title=page_meta.get("title", f"Page {page_meta['page_number']}"),
                    image_data=page_data,
                    image_format=page_meta.get("image_format", "PNG"),
                )
            )

        # Add new back cover as last page
        back_cover_page = AssembledPage(
            page_number=len(pages_meta),
            title="Back Cover",
            image_data=back_cover_data,
            image_format="PNG",
        )
        assembled_pages.append(back_cover_page)

        # Generate PDF
        import tempfile

        pdf_path = Path(tempfile.gettempdir()) / f"ebook_{ebook_id}_back_regenerated.pdf"

        # Split into cover and content pages for assembly
        cover_page = assembled_pages[0]
        content_pages = assembled_pages[1:]

        await self.assembly_service.assemble_ebook(
            cover=cover_page,
            pages=content_pages,
            output_path=str(pdf_path),
        )

        logger.info(f"📄 PDF regenerated with new back cover: {pdf_path}")

        # Step 5: Upload to Google Drive
        if self.file_storage.is_available():
            try:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                filename = f"{ebook.title or 'coloring_book'}_back_regenerated.pdf"
                upload_result = await self.file_storage.upload_ebook(
                    file_bytes=pdf_bytes,
                    filename=filename,
                    metadata={
                        "title": ebook.title or "Untitled",
                        "author": ebook.author or "Unknown",
                        "ebook_id": str(ebook_id),
                        "back_cover_regenerated": "true",
                    },
                )

                # Update ebook with new Drive info
                ebook.drive_id = upload_result.get("storage_id")
                ebook.preview_url = upload_result.get("storage_url")

                logger.info(f"✅ Uploaded to Drive: {ebook.drive_id}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to upload to Drive: {e}")
                # Continue anyway, update with local file path
                ebook.preview_url = f"file://{pdf_path}"

        else:
            logger.warning("⚠️ Google Drive not available, using local file")
            ebook.preview_url = f"file://{pdf_path}"

        # Step 6: Update structure_json with new back cover
        # Replace last page (old back cover) with new back cover
        updated_pages_meta = pages_meta[:-1]  # Keep all except last
        updated_pages_meta.append(
            {
                "page_number": len(pages_meta),
                "title": "Back Cover",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(back_cover_data).decode(),
            }
        )

        ebook.structure_json = {"pages_meta": updated_pages_meta}

        # Step 7: Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)
        logger.info(f"✅ Ebook {ebook_id} updated with new back cover")

        return updated_ebook

    def _build_back_cover_prompt(self, ebook: Ebook, front_cover_bytes: bytes) -> str:
        """Build back cover prompt from ebook metadata and front cover.

        Args:
            ebook: Ebook entity
            front_cover_bytes: Front cover bytes for color extraction

        Returns:
            Back cover prompt
        """
        theme = ebook.theme_id or "coloring book"
        audience = ebook.audience or "children"

        # Extract background color from front cover
        bg_color = extract_dominant_color_exact(front_cover_bytes)
        bg_hex = "#{:02x}{:02x}{:02x}".format(*bg_color)

        return (
            f"Create a simple LINE ART illustration for a {theme} "
            f"coloring book back cover.\n"
            f"\n"
            f"STYLE REQUIREMENTS:\n"
            f"- BLACK LINE ART ONLY (coloring book outline style)\n"
            f"- Background color: {bg_hex} (solid color, same as front cover)\n"
            f"- Clean, thick black lines (2-3px)\n"
            f"- NO interior shading, NO gradients, NO text\n"
            f"- Simple, centered composition\n"
            f"- Theme: {theme}\n"
            f"- Simpler than front cover (this is the back)\n"
            f"- Full-bleed design filling the entire frame\n"
            f"\n"
            f"IMPORTANT - BARCODE SPACE:\n"
            f"- MUST leave a PLAIN WHITE EMPTY RECTANGLE in the bottom-right corner\n"
            f"- DO NOT draw any barcode, lines, or patterns in this space\n"
            f"- Just a solid white empty box\n"
            f"- Rectangle size: approximately 15% of image width, 8% of image height\n"
            f"- Position: bottom-right corner with small margin from edges\n"
            f"- Keep all illustrations AWAY from this white rectangle area\n"
            f"\n"
            f"Examples for {theme} theme:\n"
            f"- Pirates: Simple ship outline, treasure chest, compass\n"
            f"- Unicorns: Single unicorn silhouette, stars, rainbow outline\n"
            f"- Dinosaurs: T-Rex outline, palm trees, volcano\n"
            f"\n"
            f"Target age: {audience}"
        )
