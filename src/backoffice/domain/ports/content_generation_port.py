from abc import ABC, abstractmethod

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure


class ContentGenerationPort(ABC):
    """Port for AI-based ebook content generation"""

    @abstractmethod
    async def generate_ebook_structure(
        self, prompt: str, config: EbookConfig | None = None, theme_name: str | None = None
    ) -> EbookStructure:
        """Generate structured ebook content from a user prompt

        Args:
            prompt: User input describing the desired ebook content
            config: Optional configuration including chapter/page counts
            theme_name: Optional theme name for theme-based generation

        Returns:
            EbookStructure: Complete ebook structure with metadata and content

        Raises:
            ContentGenerationError: If content generation fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the content generation service is available

        Returns:
            bool: True if service can be used for generation
        """
        pass
