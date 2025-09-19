import logging

from backoffice.domain.usecases.create_ebook import EbookProcessor
from backoffice.infrastructure.adapters.auth.google_auth import GoogleAuthService
from backoffice.infrastructure.adapters.sources.google_drive_adapter import GoogleDriveAdapter
from backoffice.infrastructure.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class OpenAIEbookProcessor(EbookProcessor):
    """OpenAI-based ebook processor implementation."""

    def __init__(self):
        self.openai_service = OpenAIService()

        # Initialize Google Drive adapter
        try:
            auth_service = GoogleAuthService("credentials/google_credentials.json")
            self.drive_adapter = GoogleDriveAdapter(auth_service)
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive adapter: {str(e)}")
            self.drive_adapter = None

    async def generate_ebook_from_prompt(self, prompt: str) -> dict[str, str | None]:
        """Generate ebook content using OpenAI and upload to Google Drive.

        Args:
            prompt: User prompt for ebook generation

        Returns:
            dict: Generated ebook metadata with real Google Drive upload
        """
        try:
            # Generate content using OpenAI
            logger.info(f"Generating ebook content for prompt: {prompt[:50]}...")
            content_data = await self.openai_service.generate_ebook_content(prompt)

            # Upload to Google Drive if available
            if self.drive_adapter:
                logger.info("Uploading ebook to Google Drive...")
                drive_data = await self.drive_adapter.upload_ebook(
                    title=content_data["title"],
                    content=content_data["content"],
                    author=content_data["author"],
                )
                return dict(drive_data)
            else:
                # Fallback if Google Drive is not available
                logger.warning("Google Drive not available, returning content without upload")
                return {
                    "title": content_data["title"],
                    "author": content_data["author"],
                    "drive_id": None,
                    "preview_url": None,
                }

        except Exception as e:
            logger.error(f"Error in ebook generation process: {str(e)}")
            # Re-raise the exception instead of hiding it with fallback data
            raise Exception(f"Échec de la génération de l'ebook: {str(e)}") from e
