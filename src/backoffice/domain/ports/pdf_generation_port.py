"""Port for PDF generation operations"""

from abc import ABC, abstractmethod
from pathlib import Path

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import EbookStructure


class PDFGenerationPort(ABC):
    """Abstract port for PDF generation"""

    @abstractmethod
    async def generate_pdf_from_structure(
        self,
        ebook_structure: EbookStructure,
        config: EbookConfig,
        output_path: Path | str,
    ) -> Path:
        """
        Generate a PDF file from an ebook structure.

        Args:
            ebook_structure: The ebook structure to render
            config: Configuration for PDF generation
            output_path: Where to save the generated PDF

        Returns:
            Path to the generated PDF file

        Raises:
            PDFGenerationError: If PDF generation fails
        """
        pass

    @abstractmethod
    async def regenerate_cover(
        self,
        ebook_structure: EbookStructure,
        config: EbookConfig,
        cover_data: dict,
    ) -> EbookStructure:
        """
        Regenerate the cover page of an ebook.

        Args:
            ebook_structure: Existing ebook structure
            config: Ebook configuration
            cover_data: New cover data (title, image_url, etc.)

        Returns:
            Updated ebook structure with new cover

        Raises:
            PDFGenerationError: If cover regeneration fails
        """
        pass


class PDFGenerationError(Exception):
    """Exception raised when PDF generation fails"""

    pass
