import logging

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure
from backoffice.domain.ports.content_generation_port import ContentGenerationPort
from backoffice.domain.services.content_parser import ContentParser
from backoffice.infrastructure.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class ContentGenerationError(Exception):
    pass


class OpenAIContentAdapter(ContentGenerationPort):
    """OpenAI content generation adapter implementing ContentGenerationPort"""

    def __init__(self, openai_service: OpenAIService | None = None):
        self.openai_service = openai_service or OpenAIService()
        self.content_parser = ContentParser()
        logger.info("OpenAIContentAdapter initialized")

    def is_available(self) -> bool:
        """Check if OpenAI service is available"""
        return self.openai_service.client is not None

    async def generate_ebook_structure(
        self, prompt: str, config: EbookConfig | None = None, theme_name: str | None = None
    ) -> EbookStructure:
        """Generate structured ebook content from prompt using OpenAI"""
        try:
            logger.info(f"Generating ebook structure from prompt: {prompt[:50]}...")

            # Generate JSON content using OpenAI service
            json_data = await self.openai_service.generate_ebook_json(
                prompt, config=config, theme_name=theme_name
            )

            # Parse JSON into EbookStructure
            ebook_structure = self.content_parser.parse_ebook_structure(json_data["content"])

            logger.info(f"Successfully generated ebook structure: '{ebook_structure.meta.title}'")
            return ebook_structure

        except Exception as e:
            logger.error(f"Error generating ebook structure: {str(e)}")
            raise ContentGenerationError(f"Failed to generate ebook structure: {str(e)}") from e

    async def generate_ebook_content_legacy(self, prompt: str) -> dict[str, str]:
        """Legacy method for backward compatibility"""
        try:
            logger.info("Using legacy content generation method")
            return await self.openai_service.generate_ebook_content(prompt)
        except Exception as e:
            logger.error(f"Error in legacy content generation: {str(e)}")
            raise ContentGenerationError(f"Failed to generate legacy content: {str(e)}") from e

    # Additional methods for flexibility
    async def generate_json_content(self, prompt: str) -> dict[str, str]:
        """Generate raw JSON content (for advanced use cases)"""
        return await self.openai_service.generate_ebook_json(prompt)

    def get_service_info(self) -> dict[str, str]:
        """Get information about the underlying service"""
        return {
            "provider": "OpenAI",
            "model": "gpt-4o-mini",
            "available": str(self.is_available()),
            "api_key_configured": str(self.openai_service.api_key is not None),
        }
