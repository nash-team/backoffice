from abc import ABC, abstractmethod

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure


class EbookGeneratorPort(ABC):
    """Port for ebook generation in different formats (PDF, EPUB, etc.)"""

    @abstractmethod
    def generate_ebook(self, ebook_structure: EbookStructure, config: EbookConfig) -> bytes:
        """Generate ebook bytes from structure and configuration

        Args:
            ebook_structure: The structured ebook content
            config: Configuration for generation (format, styling, etc.)

        Returns:
            bytes: The generated ebook file as bytes

        Raises:
            EbookGenerationError: If generation fails
        """
        pass

    @abstractmethod
    def supports_format(self, format_type: str) -> bool:
        """Check if this generator supports the given format

        Args:
            format_type: The format to check (e.g., "pdf", "epub")

        Returns:
            bool: True if format is supported
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats

        Returns:
            list[str]: List of supported format strings
        """
        pass
