from typing import Protocol

from backoffice.domain.entities.ebook import Ebook, EbookConfig, EbookStatus
from backoffice.domain.entities.image_page import ImagePage
from backoffice.domain.ports.ebook.ebook_port import EbookPort


class EbookProcessor(Protocol):
    """Protocol for external ebook processing services."""

    async def generate_ebook_from_prompt(
        self,
        prompt: str,
        config: EbookConfig | None = None,
        title: str | None = None,
        ebook_type: str | None = None,
        theme_name: str | None = None,
        image_pages: list[ImagePage] | None = None,
    ) -> dict:
        """Generate ebook content and upload to external storage.

        Returns:
            dict: Contains 'title', 'author', 'drive_id', 'preview_url'
        """
        ...


class CreateEbookUseCase:
    """Use case for creating a new ebook from a prompt."""

    def __init__(self, ebook_repository: EbookPort, ebook_processor: EbookProcessor) -> None:
        self.ebook_repository = ebook_repository
        self.ebook_processor = ebook_processor

    async def execute(
        self,
        prompt: str,
        config: EbookConfig | None = None,
        title: str | None = None,
        ebook_type: str | None = None,
        theme_name: str | None = None,
        image_pages: list[ImagePage] | None = None,
        number_of_chapters: int | None = None,
        number_of_pages: int | None = None,
    ) -> Ebook:
        """Execute ebook creation workflow.

        Args:
            prompt: User prompt for ebook generation
            config: Optional ebook configuration

        Returns:
            Ebook: Created ebook entity with DRAFT status

        Raises:
            ValueError: If prompt is invalid
            Exception: If processing or persistence fails
        """
        # Business rule: validate prompt
        if not prompt or len(prompt.strip()) < 10:
            raise ValueError("Le prompt doit contenir au moins 10 caractères")

        if len(prompt) > 2000:
            raise ValueError("Le prompt ne peut pas dépasser 2000 caractères")

        # Use default config if none provided
        if config is None:
            config = EbookConfig()

        # Update config with chapter/page counts if provided
        if number_of_chapters is not None:
            config.number_of_chapters = number_of_chapters
        if number_of_pages is not None:
            config.number_of_pages = number_of_pages

        # Create ebook with initial PENDING status
        ebook_data = await self.ebook_processor.generate_ebook_from_prompt(
            prompt=prompt,
            config=config,
            title=title,
            ebook_type=ebook_type,
            theme_name=theme_name,
            image_pages=image_pages,
        )

        # Create ebook entity
        ebook = Ebook(
            id=0,  # Will be set by repository
            title=ebook_data["title"],
            author=ebook_data["author"],
            status=EbookStatus.DRAFT,
            drive_id=ebook_data.get("drive_id"),
            preview_url=ebook_data.get("preview_url"),
            created_at=None,  # Will be set by repository
            config=config,
        )

        # Persist ebook
        created_ebook = await self.ebook_repository.create(ebook)

        return created_ebook
