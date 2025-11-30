"""Port for image editing (targeted corrections)."""

from abc import ABC, abstractmethod

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec


class ImageEditPort(ABC):
    """Port for editing existing images with targeted corrections.

    This port is used for applying specific corrections to existing images
    without regenerating them from scratch. Use cases:
    - Fix specific details (e.g., "replace 5 toes with 3 toes")
    - Remove unwanted elements (e.g., "remove colors")
    - Adjust specific parts (e.g., "make the tail longer")

    Different from generation:
    - Generation: Creates new image from text prompt only
    - Editing: Modifies existing image based on text instructions
    """

    @abstractmethod
    async def edit_image(
        self,
        image_bytes: bytes,
        edit_prompt: str,
        spec: ImageSpec,
    ) -> bytes:
        """Edit an existing image based on text instructions.

        Args:
            image_bytes: Original image data as bytes (PNG format)
            edit_prompt: Text instructions for editing (e.g., "replace 5 toes with 3")
            spec: Image specifications (dimensions, format, etc.)

        Returns:
            Edited image data as bytes

        Raises:
            DomainError: If editing fails with actionable error
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass
