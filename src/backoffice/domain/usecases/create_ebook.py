from typing import Protocol

from backoffice.domain.entities.ebook import Ebook, EbookConfig, EbookStatus
from backoffice.infrastructure.ports.repositories.ebook_repository_port import (
    EbookRepositoryPort as EbookRepository,
)


class EbookProcessor(Protocol):
    """Protocol for external ebook processing services."""

    async def generate_ebook_from_prompt(
        self, prompt: str, config: EbookConfig | None = None
    ) -> dict:
        """Generate ebook content and upload to external storage.

        Returns:
            dict: Contains 'title', 'author', 'drive_id', 'preview_url'
        """
        ...


class CreateEbookUseCase:
    """Use case for creating a new ebook from a prompt."""

    def __init__(self, ebook_repository: EbookRepository, ebook_processor: EbookProcessor) -> None:
        self.ebook_repository = ebook_repository
        self.ebook_processor = ebook_processor

    async def execute(self, prompt: str, config: EbookConfig | None = None) -> Ebook:
        """Execute ebook creation workflow.

        Args:
            prompt: User prompt for ebook generation
            config: Optional ebook configuration

        Returns:
            Ebook: Created ebook entity with PENDING status

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

        # Create ebook with initial PENDING status
        ebook_data = await self.ebook_processor.generate_ebook_from_prompt(prompt, config)

        # Create ebook entity
        ebook = Ebook(
            id=0,  # Will be set by repository
            title=ebook_data["title"],
            author=ebook_data["author"],
            status=EbookStatus.PENDING,
            drive_id=ebook_data.get("drive_id"),
            preview_url=ebook_data.get("preview_url"),
            created_at=None,  # Will be set by repository
            config=config,
        )

        # Persist ebook
        created_ebook = await self.ebook_repository.create(ebook)

        return created_ebook
