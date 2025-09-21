from abc import ABC, abstractmethod

from backoffice.domain.entities.ebook_structure import EbookStructure


class ContentGenerationPort(ABC):
    """Port for AI-based ebook content generation"""

    @abstractmethod
    async def generate_ebook_structure(self, prompt: str) -> EbookStructure:
        """Generate structured ebook content from a user prompt

        Args:
            prompt: User input describing the desired ebook content

        Returns:
            EbookStructure: Complete ebook structure with metadata and content

        Raises:
            ContentGenerationError: If content generation fails
        """
        pass

    @abstractmethod
    async def generate_ebook_content_legacy(self, prompt: str) -> dict[str, str]:
        """Legacy method for backward compatibility

        Returns:
            dict: Contains 'title', 'content', 'author' keys
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the content generation service is available

        Returns:
            bool: True if service can be used for generation
        """
        pass
