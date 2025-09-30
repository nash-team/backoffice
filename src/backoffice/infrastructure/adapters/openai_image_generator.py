import base64
import logging
from io import BytesIO

import httpx
from PIL import Image

from backoffice.domain.constants import (
    CONTENT_MIN_PIXELS_SQUARE,
    COVER_MIN_PIXELS_SQUARE,
    PageFormat,
)
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

    async def generate_image_from_prompt(
        self,
        prompt: str,
        size: str = "1024x1024",
        is_cover: bool = False,
        page_format: PageFormat = PageFormat.A4,
    ) -> bytes:
        """Generate an image from a text prompt using DALL-E with appropriate resolution"""
        try:
            # Determine optimal size based on usage and format
            if page_format == PageFormat.SQUARE_8_5:
                if is_cover:
                    # Use highest quality for covers (DALL-E max is 1024x1024, we'll upscale later)
                    size = "1024x1024"
                    quality = "hd"
                    target_pixels = COVER_MIN_PIXELS_SQUARE
                    target_info = f"cover (target: {target_pixels}x{target_pixels})"
                else:
                    # Use standard quality for content
                    size = "1024x1024"
                    quality = "standard"
                    target_pixels = CONTENT_MIN_PIXELS_SQUARE
                    target_info = f"content (target: {target_pixels}x{target_pixels})"
            else:
                # A4 or other formats
                size = "1024x1024"
                quality = "standard"
                target_info = "A4 format"

            logger.info(
                f"Generating {quality} quality image for {target_info} "
                f"from prompt: {prompt[:100]}..."
            )

            if not self.is_available():
                logger.warning("OpenAI service not available, using fallback")
                return await self._create_fallback_image()

            # Create image using DALL-E with base64 response to avoid URL download issues
            response = await self.openai_service.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
                response_format="b64_json",  # Request base64 directly instead of URL
            )

            # Get base64 data directly from response
            image_b64 = response.data[0].b64_json
            if image_b64:
                image_data = base64.b64decode(image_b64)

                # Upscale if needed for print quality
                if page_format == PageFormat.SQUARE_8_5:
                    image_data = self._upscale_image_for_print(image_data, is_cover, page_format)

                return image_data
            else:
                # Fallback if b64_json is not available
                logger.warning("No base64 data in response, using fallback image")
                return await self._create_fallback_image()

        except Exception as e:
            logger.error(f"Error generating image with OpenAI: {str(e)}")
            # Fallback to mock image on error
            return await self._create_fallback_image()

    def _upscale_image_for_print(
        self, image_data: bytes, is_cover: bool = False, page_format: PageFormat = PageFormat.A4
    ) -> bytes:
        """
        Upscale image to meet print quality requirements

        Args:
            image_data: Original image bytes
            is_cover: True if this is a cover image
            page_format: Page format for target sizing

        Returns:
            Upscaled image bytes
        """
        try:
            # Determine target size
            if page_format == PageFormat.SQUARE_8_5:
                if is_cover:
                    target_size = (COVER_MIN_PIXELS_SQUARE, COVER_MIN_PIXELS_SQUARE)  # 2550x2550
                else:
                    # 2175x2175
                    target_size = (CONTENT_MIN_PIXELS_SQUARE, CONTENT_MIN_PIXELS_SQUARE)
            else:
                # A4 format - no upscaling needed for now
                return image_data

            # Load image
            img = Image.open(BytesIO(image_data))
            original_size = img.size

            # Check if upscaling is needed
            if img.width >= target_size[0] and img.height >= target_size[1]:
                logger.info(f"Image already meets size requirements: {original_size}")
                return image_data

            # Upscale using high-quality resampling
            logger.info(f"Upscaling image from {original_size} to {target_size}")
            upscaled_img = img.resize(target_size, Image.Resampling.LANCZOS)

            # Save upscaled image
            output = BytesIO()
            upscaled_img.save(output, format="PNG", optimize=True)
            upscaled_data = output.getvalue()

            logger.info(
                f"Image upscaled: {len(image_data)} -> {len(upscaled_data)} bytes "
                f"({original_size} -> {target_size})"
            )

            return upscaled_data

        except Exception as e:
            logger.error(f"Error upscaling image: {e}, using original")
            return image_data

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

    async def generate_coloring_page_from_description(
        self, description: str, is_cover: bool = False
    ) -> bytes:
        """Generate a coloring page or colorful cover image designed for children
        with high print quality"""
        if is_cover:
            # For covers, create beautiful, colorful illustrations
            cover_prompt = (
                f"Create a beautiful illustration of {description}. "
                f"This is artwork that will be used on a children's book cover. "
                f"Do not draw a book, cover, frame, or any publishing elements. "
                f"Just draw the subject: {description}. "
                f"Use bright, colorful, child-friendly art style. "
                f"High quality illustration with no text."
            )
            prompt_to_use = cover_prompt
        else:
            # For coloring pages, keep the original black and white style
            coloring_prompt = (
                f"Create a simple black and white coloring book page of {description}. "
                f"Use thick black outlines (5-8 pixels), no shading or gradients, "
                f"simple shapes that are easy for children to color. "
                f"White background with clear boundaries between different areas to color. "
                f"Child-friendly and age-appropriate design."
            )
            prompt_to_use = coloring_prompt

        return await self.generate_image_from_prompt(
            prompt_to_use,
            size="1024x1024",
            is_cover=is_cover,
            page_format=PageFormat.SQUARE_8_5,
        )
