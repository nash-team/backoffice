"""OpenRouter provider for cover generation (Gemini 2.5 Flash Image Preview)."""

import base64
import logging
import os
from io import BytesIO

import httpx
from PIL import Image

from backoffice.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.domain.ports.content_page_generation_port import ContentPageGenerationPort
from backoffice.domain.ports.cover_generation_port import CoverGenerationPort

logger = logging.getLogger(__name__)


class OpenRouterCoverProvider(CoverGenerationPort, ContentPageGenerationPort):
    """OpenRouter provider for covers and pages using Gemini 2.5 Flash Image Preview.

    ⚠️ IMPORTANT: Only Gemini 2.5 Flash Image Preview supports image generation via OpenRouter.

    Model: google/gemini-2.5-flash-image-preview

    Supports both:
    - Colorful covers (ColorMode.COLOR)
    - B&W coloring pages (ColorMode.BLACK_WHITE)
    """

    def __init__(self, model: str | None = None):
        """Initialize OpenRouter provider.

        Args:
            model: Specific model to use (defaults to Gemini 2.5 Flash Image Preview)
        """
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        if self.api_key:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info(f"OpenRouterCoverProvider initialized: {self.model}")
        else:
            self.client = None
            logger.warning("LLM_API_KEY not found")

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.client is not None

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization.

        Returns:
            False - OpenRouter generates raster images (PNG)
        """
        return False

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a colorful cover image.

        Args:
            prompt: Text description of the cover
            spec: Image specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility

        Returns:
            Cover image as bytes

        Raises:
            DomainError: If generation fails
        """
        if not self.is_available():
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="OpenRouter provider not available",
                actionable_hint="Configure LLM_API_KEY in .env",
                context={"provider": "openrouter", "model": self.model},
            )

        # Validate model supports image generation
        if "gemini" not in self.model.lower() or "image" not in self.model.lower():
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message=f"Model {self.model} doesn't support image generation via OpenRouter",
                actionable_hint="Use google/gemini-2.5-flash-image-preview",
                context={"provider": "openrouter", "model": self.model},
            )

        # Build prompt based on color mode
        if spec.color_mode == ColorMode.BLACK_WHITE:
            # B&W coloring page style
            full_prompt = (
                f"Create a simple black and white line art coloring page illustration. "
                f"IMPORTANT: Use ONLY black lines on white background, NO colors, NO gray shading. "
                f"Thick black outlines, clean lines, simple shapes perfect for children to color. "
                f"Full-bleed design filling the entire frame. "
                f"Content: {prompt}"
            )
        else:
            # Colorful cover style
            full_prompt = (
                f"Create a vibrant, colorful cover illustration perfect for a children's book. "
                f"IMPORTANT: The illustration must fill the ENTIRE frame edge-to-edge "
                f"with NO white margins or borders. "
                f"Full-bleed design - the main subject should extend to all edges of the image. "
                f"Rich colors, engaging composition. "
                f"Content: {prompt}"
            )

        logger.info(f"Generating cover via OpenRouter: {full_prompt[:100]}...")

        try:
            # Generate via chat endpoint (Gemini-specific approach)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt,
                    }
                ],
                max_tokens=1000,
                temperature=0.7 if seed is None else 0.3,
                # Note: OpenRouter doesn't support seed for image generation yet
            )

            # Extract image from response
            image_bytes = self._extract_image_from_response(response)

            # Resize to spec if needed
            if spec.width_px != 1024 or spec.height_px != 1024:
                image = Image.open(BytesIO(image_bytes))
                image = image.resize((spec.width_px, spec.height_px), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_bytes = buffer.getvalue()

            logger.info(f"✅ Generated cover: {len(image_bytes)} bytes")
            return image_bytes

        except Exception as e:
            logger.error(f"❌ OpenRouter generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"OpenRouter generation failed: {str(e)}",
                actionable_hint="Check LLM_API_KEY validity and model availability",
                context={"provider": "openrouter", "model": self.model, "error": str(e)},
            ) from e

    async def generate_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a content page (delegates to generate_cover with same logic).

        Args:
            prompt: Text description of the page
            spec: Image specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility

        Returns:
            Page image as bytes

        Raises:
            DomainError: If generation fails
        """
        return await self.generate_cover(prompt, spec, seed)

    def _download_image_sync(self, url: str) -> bytes:
        """Download image from URL synchronously.

        Args:
            url: URL to download from

        Returns:
            Image data as bytes
        """
        import asyncio

        async def download():
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content

        return asyncio.run(download())

    def _extract_image_from_response(self, response) -> bytes:
        """Extract image bytes from OpenRouter response.

        Args:
            response: OpenRouter API response

        Returns:
            Image bytes

        Raises:
            DomainError: If image extraction fails
        """
        # Try multiple extraction strategies
        try:
            message = response.choices[0].message

            # Strategy 0: Check for images array in message (Gemini 2.5 format)
            if hasattr(message, "images") and message.images:
                logger.info("📸 Found images array in message (Gemini format)")
                first_image = message.images[0]

                # Extract from image_url.url
                if isinstance(first_image, dict) and "image_url" in first_image:
                    image_url = first_image["image_url"]["url"]

                    # Check if it's base64 data URL
                    if "base64," in image_url:
                        logger.info("Extracting base64 image from images array...")
                        base64_data = image_url.split("base64,", 1)[1]
                        return base64.b64decode(base64_data)

                    # Check if it's HTTP URL
                    if image_url.startswith("http"):
                        logger.info("Downloading image from images array URL...")
                        return self._download_image_sync(image_url)

            # Strategy 1: Direct content parsing (for other models)
            content = message.content

            if isinstance(content, str):
                # Look for base64 image data
                if "base64," in content:
                    # Extract base64 data after comma
                    base64_data = content.split("base64,", 1)[1].split('"')[0]
                    return base64.b64decode(base64_data)

                # Look for image URL
                if content.startswith("http"):
                    logger.info("Downloading image from URL...")
                    return self._download_image_sync(content)

            # Strategy 2: Check for image data in response metadata
            if hasattr(response, "data") and response.data:
                for item in response.data:
                    if hasattr(item, "b64_json"):
                        return base64.b64decode(item.b64_json)
                    if hasattr(item, "url"):
                        logger.info("Downloading from data URL...")
                        return self._download_image_sync(item.url)

        except Exception as e:
            logger.error(f"Failed to extract image: {str(e)}")

        # If all strategies fail
        raise DomainError(
            code=ErrorCode.PROVIDER_TIMEOUT,
            message=f"Failed to extract image from {self.model} response",
            actionable_hint="Model might not support image generation or response format changed",
            context={
                "provider": "openrouter",
                "model": self.model,
                "response_type": type(response).__name__,
            },
        )
