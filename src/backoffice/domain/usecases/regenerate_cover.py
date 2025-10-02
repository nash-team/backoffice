"""Use case for regenerating ebook cover (V1 slim)."""

import logging
from pathlib import Path

from backoffice.domain.cover_generation import CoverGenerationService
from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.domain.pdf_assembly import PDFAssemblyService
from backoffice.domain.ports.assembly_port import AssembledPage
from backoffice.domain.ports.ebook.ebook_port import EbookPort
from backoffice.domain.ports.file_storage_port import FileStoragePort

logger = logging.getLogger(__name__)


class RegenerateCoverUseCase:
    """Regenerate the cover of an ebook (V1 slim).

    V1 approach:
    - Only works for ebooks in PENDING status
    - Uses CoverGenerationService from new architecture
    - Regenerates PDF with new cover
    - Uploads to Google Drive
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        cover_service: CoverGenerationService,
        assembly_service: PDFAssemblyService,
        file_storage: FileStoragePort,
    ):
        """Initialize regenerate cover use case.

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
        """Regenerate the cover of an ebook.

        Args:
            ebook_id: ID of the ebook
            prompt_override: Optional custom prompt for cover generation

        Returns:
            Updated ebook with new cover

        Raises:
            ValueError: If ebook not found or not in PENDING status
        """
        # Retrieve the ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise ValueError(f"Ebook with id {ebook_id} not found")

        # Business rule: only DRAFT ebooks can have their cover regenerated
        if ebook.status != EbookStatus.DRAFT:
            raise ValueError(
                f"Cannot regenerate cover for ebook with status {ebook.status.value}. "
                f"Only DRAFT ebooks can be modified."
            )

        # Business rule: ebook must have structure_json with pages metadata
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise ValueError(
                "Cannot regenerate cover: ebook structure is missing. "
                "Please regenerate the entire ebook instead."
            )

        logger.info(f"🔄 Regenerating cover for ebook {ebook_id}: {ebook.title}")

        # Step 1: Build cover prompt
        if prompt_override:
            cover_prompt = prompt_override
            logger.info(f"Using custom prompt: {cover_prompt}")
        else:
            # Build prompt from ebook metadata
            cover_prompt = self._build_cover_prompt(ebook)
            logger.info("Using auto-generated prompt")

        # Step 2: Generate new cover
        cover_spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.COLOR,
        )

        cover_data = await self.cover_service.generate_cover(
            prompt=cover_prompt,
            spec=cover_spec,
            seed=None,  # Random cover each time
        )

        logger.info(f"✅ Cover regenerated: {len(cover_data)} bytes")

        # Step 3: Rebuild PDF with new cover
        # Extract pages metadata from structure_json
        pages_meta = ebook.structure_json["pages_meta"]

        # Build assembled pages
        cover_page = AssembledPage(
            page_number=0,
            title=ebook.title or "Cover",
            image_data=cover_data,
            image_format="PNG",
        )

        # Only include content pages (skip old cover at page_number=0)
        content_pages = []
        for page_meta in pages_meta:
            # Skip the old cover (page_number=0)
            if page_meta["page_number"] == 0:
                continue

            # Pages are stored as base64 in structure_json
            import base64

            page_data = base64.b64decode(page_meta["image_data_base64"])
            content_pages.append(
                AssembledPage(
                    page_number=page_meta["page_number"],
                    title=page_meta.get("title", f"Page {page_meta['page_number']}"),
                    image_data=page_data,
                    image_format=page_meta.get("image_format", "PNG"),
                )
            )

        # Generate PDF
        import tempfile

        pdf_path = Path(tempfile.gettempdir()) / f"ebook_{ebook_id}_regenerated.pdf"
        await self.assembly_service.assemble_ebook(
            cover=cover_page,
            pages=content_pages,
            output_path=str(pdf_path),
        )

        logger.info(f"📄 PDF regenerated: {pdf_path}")

        # Step 4: Upload to Google Drive
        if self.file_storage.is_available():
            try:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                filename = f"{ebook.title or 'coloring_book'}_regenerated.pdf"
                upload_result = await self.file_storage.upload_ebook(
                    file_bytes=pdf_bytes,
                    filename=filename,
                    metadata={
                        "title": ebook.title or "Untitled",
                        "author": ebook.author or "Unknown",
                        "ebook_id": str(ebook_id),
                        "regenerated": "true",
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

        # Step 5: Update structure_json with new cover
        import base64

        # Replace old cover (page_number=0) with new cover in structure_json
        updated_pages_meta = [
            {
                "page_number": 0,
                "title": "Cover",
                "image_format": "PNG",
                "image_data_base64": base64.b64encode(cover_data).decode(),
            }
        ]
        # Keep all other pages (skip old cover)
        for page_meta in pages_meta:
            if page_meta["page_number"] != 0:
                updated_pages_meta.append(page_meta)

        ebook.structure_json = {"pages_meta": updated_pages_meta}

        # Step 6: Save updated ebook
        updated_ebook = await self.ebook_repository.save(ebook)
        logger.info(f"✅ Ebook {ebook_id} updated with new cover")

        return updated_ebook

    def _build_cover_prompt(self, ebook: Ebook) -> str:
        """Build cover prompt from ebook metadata.

        Args:
            ebook: Ebook entity

        Returns:
            Cover prompt
        """
        theme = ebook.theme_id or "coloring book"
        audience = ebook.audience or "children"

        return (
            f"Create a vibrant, colorful cover for a children's coloring book. "
            f"Title: '{ebook.title}'. "
            f"Theme: {theme}. "
            f"Target age: {audience}. "
            f"Style: Engaging, playful, child-friendly. "
            f"Full-bleed illustration with rich colors."
        )
