"""Port for cover image generation."""

from abc import ABC, abstractmethod

from backoffice.domain.entities.generation_request import ImageSpec


class CoverGenerationPort(ABC):
    """Port for generating cover images (colorful, full-bleed)."""

    @abstractmethod
    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a cover image.

        Args:
            prompt: Text prompt describing the cover
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

    @abstractmethod
    async def remove_text_from_cover(
        self,
        cover_bytes: bytes,
    ) -> bytes:
        """Remove text from cover to create back cover using AI vision.

        Provider-agnostic method: each provider implements its own logic
        (Gemini Vision for OpenRouter, etc.)

        Args:
            cover_bytes: Original cover image (with text)

        Returns:
            Same image without text (for back cover)

        Raises:
            DomainError: If transformation fails
        """
        pass
