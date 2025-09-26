import logging

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.image_page import ImagePage
from backoffice.domain.usecases.create_ebook import EbookProcessor
from backoffice.domain.usecases.generate_ebook import GenerateEbookUseCase
from backoffice.infrastructure.adapters.google_drive_storage_adapter import (
    GoogleDriveStorageAdapter,
)
from backoffice.infrastructure.adapters.openai_content_adapter import OpenAIContentAdapter
from backoffice.infrastructure.adapters.pdf_generator_adapter import PDFGeneratorAdapter

logger = logging.getLogger(__name__)


class OpenAIEbookProcessor(EbookProcessor):
    """OpenAI-based ebook processor using hexagonal architecture with ports."""

    def __init__(self, user_email: str | None = None):
        # Initialize adapters
        self.content_adapter = OpenAIContentAdapter()
        self.pdf_adapter = PDFGeneratorAdapter()
        # Pass user email to storage adapter (pour toi seul au début)
        self.storage_adapter = GoogleDriveStorageAdapter(default_user_email=user_email)

        # Initialize use case with dependency injection
        self.generate_ebook_use_case = GenerateEbookUseCase(
            content_generator=self.content_adapter,
            ebook_generator=self.pdf_adapter,
            file_storage=self.storage_adapter,
        )

        logger.info(
            f"OpenAIEbookProcessor initialized with hexagonal architecture "
            f"(user: {user_email or 'system'})"
        )

    async def generate_ebook_from_prompt(
        self,
        prompt: str,
        config: EbookConfig | None = None,
        title: str | None = None,
        ebook_type: str | None = None,
        theme_name: str | None = None,
        image_pages: list[ImagePage] | None = None,
    ) -> dict[str, str | int | bool | None | list[str]]:
        """Generate ebook using the new hexagonal architecture.

        Args:
            prompt: User prompt for ebook generation
            config: Ebook configuration options

        Returns:
            dict: Generated ebook metadata with upload info
        """
        try:
            if config is None:
                config = EbookConfig()

            logger.info(
                f"Using hexagonal architecture for ebook generation - "
                f"Type: {ebook_type}, Theme: {theme_name}, Prompt: {prompt[:50]}..."
            )

            # Delegate to the use case with new parameters
            result = await self.generate_ebook_use_case.execute(
                prompt=prompt,
                config=config,
                title=title,
                ebook_type=ebook_type,
                theme_name=theme_name,
                image_pages=image_pages,
            )

            # Map storage fields to expected ebook fields
            if "storage_id" in result:
                result["drive_id"] = result["storage_id"]
            if "storage_url" in result:
                result["preview_url"] = result["storage_url"]

            logger.info(
                f"Ebook generation completed via use case: '{result.get('title', 'Unknown')}'"
            )
            return result

        except Exception as e:
            logger.error(f"Error in ebook generation process: {str(e)}")
            raise Exception(f"Échec de la génération de l'ebook: {str(e)}") from e

    def get_supported_formats(self) -> list[str]:
        """Get supported ebook formats"""
        return self.generate_ebook_use_case.get_supported_formats()

    def get_service_status(self) -> dict[str, bool]:
        """Get status of all services"""
        return self.generate_ebook_use_case.get_service_status()
