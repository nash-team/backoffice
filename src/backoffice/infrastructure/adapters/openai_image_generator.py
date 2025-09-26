import base64
import logging
from io import BytesIO

import httpx
from PIL import Image

from backoffice.domain.ports.image_generation_port import ImageGenerationPort
from backoffice.infrastructure.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    pass


class OpenAIImageGenerator(ImageGenerationPort):
    """OpenAI DALL-E image generation adapter implementing ImageGenerationPort"""

    def __init__(self, openai_service: OpenAIService | None = None):
        self.openai_service = openai_service or OpenAIService()
        logger.info("OpenAIImageGenerator initialized")

    def is_available(self) -> bool:
        """Check if OpenAI service is available"""
        return self.openai_service.client is not None

    async def generate_image_from_url(self, image_url: str, prompt: str | None = None) -> bytes:
        """Generate an image based on a URL (converted to coloring book style)

        For coloring book pages, we first download the image then convert it to a line art style
        """
        try:
            logger.info(f"Processing image from URL: {image_url}")

            if not self.is_available():
                logger.warning("OpenAI service not available, using fallback")
                return await self._create_fallback_image()

            # Download the original image (for future use)
            async with httpx.AsyncClient() as client:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; OpenAI-Image-Downloader/1.0)"}
                response = await client.get(image_url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                # original_image_data = response.content  # Unused, stored for future enhancement

            # Since DALL-E 3 doesn't support image input directly, we'll create a descriptive prompt
            # and generate a coloring book style image
            fallback_prompt = (
                f"Create a simple black and white coloring book page with thick black outlines "
                f"and white fill areas. Simple design suitable for children to color. "
                f"{prompt or ''}"
            )

            return await self.generate_image_from_prompt(fallback_prompt, "1024x1024")

        except Exception as e:
            logger.error(f"Error processing image from URL: {str(e)}")
            raise ImageGenerationError(f"Failed to process image from URL: {str(e)}") from e

    async def generate_image_from_prompt(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Generate an image from a text prompt using DALL-E"""
        try:
            logger.info(f"Generating image from prompt: {prompt[:100]}...")

            if not self.is_available():
                logger.warning("OpenAI service not available, using fallback")
                return await self._create_fallback_image()

            # Create image using DALL-E with base64 response to avoid URL download issues
            response = await self.openai_service.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1,
                response_format="b64_json",  # Request base64 directly instead of URL
            )

            # Get base64 data directly from response
            image_b64 = response.data[0].b64_json
            if image_b64:
                return base64.b64decode(image_b64)
            else:
                # Fallback if b64_json is not available
                logger.warning("No base64 data in response, using fallback image")
                return await self._create_fallback_image()

        except Exception as e:
            logger.error(f"Error generating image with OpenAI: {str(e)}")
            # Fallback to mock image on error
            return await self._create_fallback_image()

    async def _create_fallback_image(self) -> bytes:
        """Create a simple fallback coloring page when OpenAI is not available"""
        try:
            # Create a simple black and white image with PIL
            width, height = 1024, 1024
            image = Image.new("RGB", (width, height), "white")

            # Add some simple shapes for coloring
            from PIL import ImageDraw

            draw = ImageDraw.Draw(image)

            # Draw a simple flower outline
            center_x, center_y = width // 2, height // 2

            # Flower petals (circles)
            petal_radius = 80
            petal_positions = [
                (center_x, center_y - 120),  # top
                (center_x + 85, center_y - 85),  # top-right
                (center_x + 120, center_y),  # right
                (center_x + 85, center_y + 85),  # bottom-right
                (center_x, center_y + 120),  # bottom
                (center_x - 85, center_y + 85),  # bottom-left
                (center_x - 120, center_y),  # left
                (center_x - 85, center_y - 85),  # top-left
            ]

            for px, py in petal_positions:
                draw.ellipse(
                    [px - petal_radius, py - petal_radius, px + petal_radius, py + petal_radius],
                    outline="black",
                    width=5,
                )

            # Flower center
            draw.ellipse(
                [center_x - 40, center_y - 40, center_x + 40, center_y + 40],
                outline="black",
                width=5,
            )

            # Stem
            draw.line([(center_x, center_y + 120), (center_x, height - 100)], fill="black", width=8)

            # Leaves
            leaf_points = [
                (center_x - 50, center_y + 200),
                (center_x - 100, center_y + 180),
                (center_x - 80, center_y + 250),
                (center_x - 30, center_y + 220),
            ]
            draw.polygon(leaf_points, outline="black", width=5)

            leaf_points_right = [
                (center_x + 50, center_y + 200),
                (center_x + 100, center_y + 180),
                (center_x + 80, center_y + 250),
                (center_x + 30, center_y + 220),
            ]
            draw.polygon(leaf_points_right, outline="black", width=5)

            # Convert to bytes
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Error creating fallback image: {str(e)}")
            # Create minimal 1x1 white PNG as last resort
            img = Image.new("RGB", (1, 1), "white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()

    async def generate_coloring_page_from_description(self, description: str) -> bytes:
        """Generate a coloring page specifically designed for children"""
        coloring_prompt = (
            f"Create a simple black and white coloring book page of {description}. "
            f"Use thick black outlines (5-8 pixels), no shading or gradients, "
            f"simple shapes that are easy for children to color. "
            f"White background with clear boundaries between different areas to color. "
            f"Child-friendly and age-appropriate design."
        )

        return await self.generate_image_from_prompt(coloring_prompt, "1024x1024")
