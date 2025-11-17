"""Port for content page generation."""

from abc import ABC, abstractmethod

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec


class ContentPageGenerationPort(ABC):
    """Port for generating content pages (B&W coloring pages)."""

    @abstractmethod
    async def generate_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a single content page.

        Args:
            prompt: Text prompt describing the page
            spec: Image specifications (dimensions, format, etc.)
            seed: Random seed for reproducibility

        Returns:
            Image data as bytes

        Raises:
            DomainError: If generation fails with actionable error
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass
