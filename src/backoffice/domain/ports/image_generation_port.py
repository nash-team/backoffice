from abc import ABC, abstractmethod


class ImageGenerationPort(ABC):
    """Port for AI-based image generation"""

    @abstractmethod
    async def generate_image_from_url(self, image_url: str, prompt: str | None = None) -> bytes:
        """Generate an image based on a URL or prompt

        Args:
            image_url: URL of an existing image to use as reference or generate from
            prompt: Optional prompt for image generation/modification

        Returns:
            bytes: Generated image data in PNG format

        Raises:
            ImageGenerationError: If image generation fails
        """
        pass

    @abstractmethod
    async def generate_image_from_prompt(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Generate an image from a text prompt

        Args:
            prompt: Text description of the desired image
            size: Image size (e.g., "1024x1024", "512x512")

        Returns:
            bytes: Generated image data in PNG format

        Raises:
            ImageGenerationError: If image generation fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the image generation service is available

        Returns:
            bool: True if service can be used for generation
        """
        pass

    @abstractmethod
    async def generate_coloring_page_from_description(
        self, description: str, is_cover: bool = False
    ) -> bytes:
        """Generate a coloring page or colorful cover image designed for children

        Args:
            description: Description of what should be in the image
            is_cover: True for colorful cover image, False for black/white coloring page

        Returns:
            bytes: Generated image data in PNG format (colorful for covers, B&W for pages)

        Raises:
            ImageGenerationError: If image generation fails
        """
        pass
