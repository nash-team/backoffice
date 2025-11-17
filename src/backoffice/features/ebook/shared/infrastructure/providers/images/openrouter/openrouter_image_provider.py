"""OpenRouter provider for image generation (Gemini 2.5 Flash Image Preview)."""

import base64
import logging
import os
from io import BytesIO

from PIL import Image

from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.ebook.shared.infrastructure.providers.images.openrouter.response_extractor import (
    OpenRouterResponseExtractor,
)
from backoffice.features.ebook.shared.infrastructure.utils.image_borders import (
    add_rounded_border_to_image,
)
from backoffice.features.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode

logger = logging.getLogger(__name__)


class OpenRouterImageProvider(CoverGenerationPort, ContentPageGenerationPort):
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
        from openai import AsyncOpenAI

        self.api_key = os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.client: AsyncOpenAI | None

        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            self.extractor = OpenRouterResponseExtractor(model=self.model or "unknown")
            logger.info(f"OpenRouterImageProvider initialized: {self.model}")
        else:
            self.client = None
            self.extractor = OpenRouterResponseExtractor(model=self.model or "unknown")
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
        if (
            not self.model
            or "gemini" not in self.model.lower()
            or "image" not in self.model.lower()
        ):
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message=f"Model {self.model} doesn't support image generation via OpenRouter",
                actionable_hint="Use google/gemini-2.5-flash-image-preview",
                context={"provider": "openrouter", "model": self.model},
            )

        # Use prompt directly from strategy (no duplication)
        # The strategy (e.g., ColoringBookStrategy) already builds the complete prompt
        full_prompt = prompt

        logger.info(
            "🎨 Generating cover via OpenRouter",
            extra={
                "model": self.model,
                "prompt_length": len(full_prompt),
                "spec": f"{spec.width_px}x{spec.height_px}",
                "color_mode": spec.color_mode.value if spec.color_mode else "default",
            },
        )
        logger.debug(f"Full prompt: {full_prompt}")

        try:
            # Generate via chat endpoint (Gemini-specific approach)
            # Gemini 2.5 Flash Image Preview requires modalities: ["image", "text"]
            assert self.model is not None  # Already validated above
            assert self.client is not None  # Already validated above
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt,
                    }
                ],
                extra_body={
                    "modalities": ["image", "text"],  # Required for Gemini image generation
                    "usage": {
                        "include": True
                    },  # Enable Usage Accounting for real cost (usage.cost)
                },
                extra_headers={
                    "HTTP-Referer": "https://ebook-generator.app",
                    "X-Title": "Ebook Generator Backoffice",
                },
                max_tokens=1000,
                temperature=0.7 if seed is None else 0.3,
                # Note: OpenRouter doesn't support seed for image generation yet
            )

            # Extract image from response
            logger.debug("Extracting image from API response...")
            image_bytes = self._extract_image_from_response(response)
            logger.debug(f"Extracted image: {len(image_bytes)} bytes (raw)")

            # Resize to spec if needed
            if spec.width_px != 1024 or spec.height_px != 1024:
                logger.debug(
                    f"Resizing image from 1024x1024 to {spec.width_px}x{spec.height_px}..."
                )
                image = Image.open(BytesIO(image_bytes))
                image = image.resize((spec.width_px, spec.height_px), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_bytes = buffer.getvalue()
                logger.debug(f"Resized image: {len(image_bytes)} bytes")

            # Add rounded border for B&W coloring pages (programmatically, not via prompt)
            if spec.color_mode == ColorMode.BLACK_WHITE:
                logger.debug("Adding rounded black border to coloring page...")
                image_bytes = self._add_rounded_border_to_image(image_bytes)
                logger.debug(f"With border: {len(image_bytes)} bytes")

            logger.info(
                "✅ Cover generated successfully",
                extra={"size_bytes": len(image_bytes), "model": self.model},
            )
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
            spec: ImageSpec specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility

        Returns:
            Page image as bytes

        Raises:
            DomainError: If generation fails
        """
        return await self.generate_cover(prompt, spec, seed)

    async def remove_text_from_cover(
        self,
        cover_bytes: bytes,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.5,
        barcode_margin_inches: float = 0.25,
    ) -> bytes:
        """Remove text from cover to create back cover using Gemini vision.

        Args:
            cover_bytes: Original cover image (with text)
            barcode_width_inches: KDP barcode width in inches (default: 2.0)
            barcode_height_inches: KDP barcode height in inches (default: 1.5)
            barcode_margin_inches: KDP barcode margin in inches (default: 0.25)

        Returns:
            Same image without text with KDP-compliant barcode space (for back cover)

        Raises:
            DomainError: If transformation fails
        """
        if not self.is_available():
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="OpenRouter provider not available",
                actionable_hint="Configure LLM_API_KEY in .env",
                context={"provider": "openrouter", "model": self.model},
            )

        logger.info("🍌 Removing text from cover with Gemini Vision (ultra-simple prompt)...")

        try:
            # Encode cover to base64
            cover_b64 = base64.b64encode(cover_bytes).decode()

            # ULTRA-SIMPLE prompt: just remove text, nothing else
            prompt_text = "Remove all text and typography from this image."

            # Call Gemini with image input + ultra-simple prompt
            assert self.model is not None  # Already validated above
            assert self.client is not None  # Already validated above
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{cover_b64}"},
                            },
                            {
                                "type": "text",
                                "text": prompt_text,
                            },
                        ],
                    }
                ],
                extra_body={
                    "modalities": ["image", "text"],
                    "usage": {
                        "include": True
                    },  # Enable Usage Accounting for real cost (usage.cost)
                },
                extra_headers={
                    "HTTP-Referer": "https://ebook-generator.app",
                    "X-Title": "Ebook Generator Backoffice",
                },
                max_tokens=1000,
                temperature=0.3,
            )

            # Extract transformed image (without text)
            image_bytes = self._extract_image_from_response(response)
            logger.info(f"✅ Text removed by Gemini: {len(image_bytes)} bytes")

            # Return image without text
            # Barcode space will be added during KDP export, not here
            logger.info(f"✅ Back cover ready (no barcode space): {len(image_bytes)} bytes")
            return image_bytes

        except Exception as e:
            logger.error(f"❌ Gemini transformation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Gemini vision transformation failed: {str(e)}",
                actionable_hint="Check if model supports image-to-image transformation",
                context={"provider": "openrouter", "model": self.model, "error": str(e)},
            ) from e

    def _add_rounded_border_to_image(
        self,
        image_bytes: bytes,
        border_width: int = 5,
        corner_radius: int = 20,
        margin: int = 50,
    ) -> bytes:
        """Add a rounded black border to the image with white margin.

        Delegates to shared utility function.

        Args:
            image_bytes: Original image bytes
            border_width: Width of the border in pixels (default: 5px)
            corner_radius: Radius for rounded corners in pixels (default: 20px)
            margin: White space between content and border in pixels (default: 50px)

        Returns:
            Image bytes with border and margin added
        """
        return add_rounded_border_to_image(
            image_bytes=image_bytes,
            border_width=border_width,
            corner_radius=corner_radius,
            margin=margin,
        )

    def _extract_image_from_response(self, response) -> bytes:
        """Extract image bytes from OpenRouter response.

        Delegates to OpenRouterResponseExtractor for clean separation of concerns.

        Args:
            response: OpenRouter API response

        Returns:
            Image bytes

        Raises:
            DomainError: If image extraction fails
        """
        return self.extractor.extract_image_from_response(response)
