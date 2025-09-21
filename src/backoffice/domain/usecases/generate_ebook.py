import logging

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.ports.content_generation_port import ContentGenerationPort
from backoffice.domain.ports.ebook_generator_port import EbookGeneratorPort
from backoffice.domain.ports.file_storage_port import FileStoragePort

logger = logging.getLogger(__name__)


class GenerateEbookUseCase:
    """Use case for generating ebooks using dependency injection with ports"""

    def __init__(
        self,
        content_generator: ContentGenerationPort,
        ebook_generator: EbookGeneratorPort,
        file_storage: FileStoragePort | None = None,
    ):
        self.content_generator = content_generator
        self.ebook_generator = ebook_generator
        self.file_storage = file_storage
        logger.info("GenerateEbookUseCase initialized with injected dependencies")

    async def execute(
        self, prompt: str, config: EbookConfig | None = None
    ) -> dict[str, str | int | bool | None]:
        """Execute the ebook generation workflow

        Args:
            prompt: User prompt for content generation
            config: Ebook configuration (format, styling, etc.)

        Returns:
            dict: Result containing title, author, storage info, etc.

        Raises:
            ValueError: If configuration is invalid
            Exception: If generation workflow fails
        """
        try:
            # Use default config if none provided
            if config is None:
                config = EbookConfig()

            logger.info(f"Starting ebook generation workflow with format: {config.format}")

            # Validate that generator supports the requested format
            if not self.ebook_generator.supports_format(config.format):
                supported = ", ".join(self.ebook_generator.get_supported_formats())
                raise ValueError(
                    f"Format '{config.format}' not supported. Supported formats: {supported}"
                )

            # Step 1: Generate content structure
            logger.info("Generating ebook content structure...")
            ebook_structure = await self.content_generator.generate_ebook_structure(prompt)

            # Step 2: Generate ebook file
            logger.info(f"Generating {config.format.upper()} file...")
            ebook_bytes = self.ebook_generator.generate_ebook(ebook_structure, config)

            # Step 3: Upload to storage (if available)
            result: dict[str, str | int | bool | None] = {
                "title": ebook_structure.meta.title,
                "author": ebook_structure.meta.author,
                "format": config.format,
                "size": len(ebook_bytes),
                "content_generation_available": self.content_generator.is_available(),
                "storage_available": self.file_storage.is_available()
                if self.file_storage
                else False,
            }

            if self.file_storage and self.file_storage.is_available():
                logger.info("Uploading ebook to storage...")
                filename = f"{ebook_structure.meta.title}.{config.format}"
                metadata = {
                    "title": ebook_structure.meta.title,
                    "author": ebook_structure.meta.author,
                    "format": config.format,
                }

                storage_result = await self.file_storage.upload_ebook(
                    file_bytes=ebook_bytes, filename=filename, metadata=metadata
                )

                # Merge storage result into final result
                result.update(storage_result)
            else:
                logger.warning("No storage service available, ebook not uploaded")
                result.update(
                    {"storage_id": None, "storage_url": None, "storage_status": "no_storage"}
                )

            logger.info(f"Ebook generation completed successfully: '{ebook_structure.meta.title}'")
            return result

        except Exception as e:
            logger.error(f"Error in ebook generation workflow: {str(e)}")
            raise Exception(f"Ebook generation failed: {str(e)}") from e

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats from the ebook generator"""
        return self.ebook_generator.get_supported_formats()

    def get_service_status(self) -> dict[str, bool]:
        """Get status of all injected services"""
        return {
            "content_generator": self.content_generator.is_available(),
            "ebook_generator": True,  # Always available (no availability check in port)
            "file_storage": self.file_storage.is_available() if self.file_storage else False,
        }
