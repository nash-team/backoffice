import base64
import logging
from dataclasses import asdict

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.image_page import ImagePage
from backoffice.domain.ports.content_generation_port import ContentGenerationPort
from backoffice.domain.ports.ebook_generator_port import EbookGeneratorPort
from backoffice.domain.ports.file_storage_port import FileStoragePort

logger = logging.getLogger(__name__)


def serialize_ebook_structure(structure_dict: dict) -> dict:
    """Convert ebook structure to JSON-serializable format (bytes to base64, enums to values)"""
    from enum import Enum

    def convert_to_serializable(obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        return obj

    return convert_to_serializable(structure_dict)


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
        self,
        prompt: str,
        config: EbookConfig | None = None,
        title: str | None = None,
        ebook_type: str | None = None,
        theme_name: str | None = None,
        image_pages: list[ImagePage] | None = None,
    ) -> dict[str, str | int | bool | None | list[str]]:
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
            ebook_structure = await self.content_generator.generate_ebook_structure(
                prompt, config=config, theme_name=theme_name
            )

            # Step 1.5: Integrate image pages if provided
            if image_pages:
                logger.info(f"Integrating {len(image_pages)} image pages into ebook structure")
                for image_page in image_pages:
                    ebook_structure.add_coloring_page_section(image_page)
                logger.info("Image pages successfully integrated")

            # Step 2: Generate ebook file
            logger.info(f"Generating {config.format.upper()} file...")
            ebook_bytes = await self.ebook_generator.generate_ebook(ebook_structure, config)

            # Step 3: Upload to storage (if available)
            # Serialize structure with bytes converted to base64
            structure_dict = asdict(ebook_structure)
            serializable_structure = serialize_ebook_structure(structure_dict)

            # ✅ DRAFT workflow: Ebook created but NOT uploaded to Drive
            # Upload will happen only after manual approval
            result: dict[str, str | int | bool | None | list[str] | dict] = {
                "title": ebook_structure.meta.title,
                "author": ebook_structure.meta.author,
                "format": config.format,
                "size": len(ebook_bytes),
                "status": "DRAFT",  # Ebook requires manual approval
                "content_generation_available": self.content_generator.is_available(),
                "storage_available": self.file_storage.is_available()
                if self.file_storage
                else False,
                "ebook_structure": serializable_structure,  # Store structure for regeneration
                "ebook_bytes": ebook_bytes,  # Keep bytes for preview and later upload
                "storage_id": None,  # Will be set after approval
                "storage_url": None,  # Will be set after approval
                "storage_status": "pending_approval",
            }

            logger.info(
                f"Ebook generated in DRAFT status: '{ebook_structure.meta.title}' "
                f"(awaiting manual approval before Drive upload)"
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
