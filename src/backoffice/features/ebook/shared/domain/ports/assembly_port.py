"""Port for PDF assembly."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AssembledPage:
    """A page ready for PDF assembly."""

    page_number: int
    title: str
    image_data: bytes
    image_format: str


class AssemblyPort(ABC):
    """Port for assembling images into PDF."""

    @abstractmethod
    async def assemble_pdf(
        self,
        cover: AssembledPage,
        pages: list[AssembledPage],
        output_path: str,
    ) -> str:
        """Assemble cover and content pages into a PDF.

        Args:
            cover: Cover page to include
            pages: Content pages to include
            output_path: Path where PDF should be saved

        Returns:
            URI to the generated PDF

        Raises:
            DomainError: If assembly fails
        """
        pass
