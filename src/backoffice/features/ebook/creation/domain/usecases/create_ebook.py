"""Use case for creating ebooks using generation strategies."""

import base64
import logging
from datetime import datetime
from typing import cast

from backoffice.features.ebook.creation.domain.events.ebook_created_event import EbookCreatedEvent
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.ports.ebook_generation_strategy_port import (
    EbookGenerationStrategyPort,
)
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.ebook.shared.domain.ports.file_storage_port import FileStoragePort
from backoffice.features.shared.domain.entities.generation_request import GenerationRequest
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class CreateEbookUseCase:
    """Use case for creating ebooks.

    Context (in Strategy pattern) that uses a generation strategy to create ebooks.
    Handles the complete workflow: generation, persistence, storage, and event emission.
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        generation_strategy: EbookGenerationStrategyPort,
        event_bus: EventBus,
        file_storage: FileStoragePort | None = None,
    ):
        """Initialize use case with dependencies.

        Args:
            ebook_repository: Repository for ebook persistence
            generation_strategy: Strategy for ebook generation (injected based on type)
            event_bus: Event bus for publishing domain events
            file_storage: Optional file storage service (e.g., Google Drive)
        """
        self.ebook_repository = ebook_repository
        self.generation_strategy = generation_strategy
        self.event_bus = event_bus
        self.file_storage = file_storage

    async def execute(self, request: GenerationRequest, is_preview: bool = False) -> Ebook:
        """Execute ebook creation workflow.

        Args:
            request: Generation request with all parameters
            is_preview: If True, mark as preview mode in structure_json

        Returns:
            Created ebook entity

        Raises:
            DomainError: If generation or persistence fails
        """
        import time

        logger.info(f"🎨 Creating ebook: {request.title} (type: {request.ebook_type.value})")

        # 1. Generate ebook using strategy (measure duration)
        start_time = time.time()
        generation_result = await self.generation_strategy.generate(request)
        generation_duration = time.time() - start_time

        logger.info(f"✅ Ebook generated: {generation_result.pdf_uri}")
        logger.info(f"   Total pages: {len(generation_result.pages_meta)}")
        logger.info(f"   Duration: {generation_duration:.2f}s")

        # 2. Create ebook entity
        ebook = Ebook(
            id=None,
            title=request.title,
            author="Generated",  # TODO: Get from user context
            created_at=datetime.now(),
            status=EbookStatus.DRAFT,
            theme_id=request.theme,
            audience=request.age_group.value,
            preview_url=generation_result.pdf_uri,
            page_count=len(generation_result.pages_meta),
        )

        # 3. Store structure in ebook
        pages_meta_serialized = [
            {
                "page_number": page.page_number,
                "title": page.title,
                "image_format": page.format,
                "image_data_base64": base64.b64encode(page.image_data).decode(),
            }
            for page in generation_result.pages_meta
        ]

        ebook.structure_json = {
            "is_preview": is_preview,
            "pages_meta": pages_meta_serialized,
        }

        # 4. Persist to database
        ebook = await self.ebook_repository.create(ebook)
        logger.info(f"💾 Ebook saved to database with ID: {ebook.id}")

        # Ensure ebook has an ID after creation (guaranteed by repository)
        if ebook.id is None:
            raise ValueError("Ebook ID should not be None after creation")

        # 5. Save PDF bytes to database for DRAFT workflow
        pdf_bytes: bytes
        try:
            import re

            pdf_path = re.sub(r"^file://", "", generation_result.pdf_uri)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            await self.ebook_repository.save_ebook_bytes(ebook.id, pdf_bytes)
            logger.info(f"✅ PDF bytes saved to database for ebook {ebook.id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save PDF bytes: {e}")

        # 6. Upload to file storage if available
        has_drive_upload = False
        if self.file_storage and self.file_storage.is_available():
            try:
                # Upload to Drive
                upload_result = await self.file_storage.upload_ebook(
                    file_bytes=pdf_bytes,
                    filename=f"{request.title}.pdf",
                    metadata={
                        "title": request.title,
                        "theme": request.theme,
                        "age_group": request.age_group.value,
                        "ebook_id": str(ebook.id),
                    },
                )

                # Update ebook with Drive info
                ebook.drive_id = upload_result.get("storage_id")
                ebook.preview_url = upload_result.get("storage_url")

                ebook = await self.ebook_repository.save(ebook)
                logger.info(f"☁️ Ebook uploaded to storage: {ebook.drive_id}")
                has_drive_upload = True

            except Exception as e:
                logger.warning(f"⚠️ Failed to upload to storage: {e}")
                # Continue anyway - ebook is already in DB with local file path

        logger.info(f"✅ Ebook creation complete: {ebook.id}")

        # 7. Emit domain event
        # ebook.id is guaranteed to be non-None after creation (checked above)
        await self.event_bus.publish(
            EbookCreatedEvent(
                ebook_id=cast(int, ebook.id),
                title=ebook.title or "Untitled",
                theme_id=ebook.theme_id or "unknown",
                audience=ebook.audience or "unknown",
                number_of_pages=len(generation_result.pages_meta),
                preview_mode=is_preview,
                has_drive_upload=has_drive_upload,
            )
        )

        return ebook
