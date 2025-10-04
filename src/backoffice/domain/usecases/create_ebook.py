"""Use case for creating ebooks using generation strategies."""

import base64
import logging
from datetime import datetime

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.entities.generation_request import GenerationRequest
from backoffice.domain.ports.ebook.ebook_port import EbookPort
from backoffice.domain.ports.ebook_generation_strategy_port import EbookGenerationStrategyPort
from backoffice.domain.ports.file_storage_port import FileStoragePort

logger = logging.getLogger(__name__)


class CreateEbookUseCase:
    """Use case for creating ebooks.

    Context (in Strategy pattern) that uses a generation strategy to create ebooks.
    Handles the complete workflow: generation, persistence, and storage.
    """

    def __init__(
        self,
        ebook_repository: EbookPort,
        generation_strategy: EbookGenerationStrategyPort,
        file_storage: FileStoragePort | None = None,
    ):
        """Initialize use case with dependencies.

        Args:
            ebook_repository: Repository for ebook persistence
            generation_strategy: Strategy for ebook generation (injected based on type)
            file_storage: Optional file storage service (e.g., Google Drive)
        """
        self.ebook_repository = ebook_repository
        self.generation_strategy = generation_strategy
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

        # Extract generation metadata if token tracker is available

        from backoffice.domain.value_objects.generation_metadata import GenerationMetadata

        generation_metadata: GenerationMetadata | None = None

        if (
            hasattr(self.generation_strategy, "token_tracker")
            and self.generation_strategy.token_tracker
        ):
            tracker = self.generation_strategy.token_tracker
            generation_cost = tracker.get_total_cost()
            prompt_tokens = tracker.get_total_prompt_tokens()
            completion_tokens = tracker.get_total_completion_tokens()

            # Extract provider and model from first usage (they're all the same)
            generation_provider = "unknown"
            generation_model = "unknown"
            if tracker.usages:
                first_usage = tracker.usages[0]
                generation_model = first_usage.model

                # Detect provider from model name using shared utility
                from backoffice.domain.utils.provider_detection import detect_provider_from_model

                generation_provider = detect_provider_from_model(generation_model)

            # Create GenerationMetadata Value Object
            generation_metadata = GenerationMetadata(
                provider=generation_provider,
                model=generation_model,
                cost=generation_cost,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_seconds=generation_duration,
                generated_at=datetime.now(),
            )

            total_tokens = prompt_tokens + completion_tokens
            logger.info(
                f"💰 Generation cost: ${generation_cost:.4f} "
                f"(Tokens: {prompt_tokens} prompt + {completion_tokens} completion "
                f"= {total_tokens} total)"
            )
            logger.info(f"🔧 Provider: {generation_provider} | Model: {generation_model}")
        else:
            logger.warning("⚠️ Token tracker not available, cost not tracked")

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
            generation_metadata=generation_metadata,  # Value Object (DDD)
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

        # Ensure ebook has an ID after creation
        assert ebook.id is not None, "Ebook ID should not be None after creation"

        # 5. Save PDF bytes to database for DRAFT workflow
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

            except Exception as e:
                logger.warning(f"⚠️ Failed to upload to storage: {e}")
                # Continue anyway - ebook is already in DB with local file path

        logger.info(f"✅ Ebook creation complete: {ebook.id}")
        return ebook
