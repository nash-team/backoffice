"""Google Gemini direct API provider for image generation (Nano Banana)."""

import base64
import logging
import os
from decimal import Decimal
from io import BytesIO

import httpx
from PIL import Image, ImageDraw

from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.ebook.shared.domain.value_objects.usage_metrics import UsageMetrics
from backoffice.features.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode

logger = logging.getLogger(__name__)


class GeminiImageProvider(CoverGenerationPort, ContentPageGenerationPort):
    """Google Gemini direct API provider using Gemini 2.5 Flash Image (Nano Banana).

    Uses Google AI Studio REST API directly (no SDK needed).
    Model: gemini-2.5-flash-image (native image generation)
    Features: Subject identity, prompt-based editing, visual reasoning
    Pricing: ~$0.04 per image (estimated)

    Supports both:
    - Colorful covers (ColorMode.COLOR)
    - B&W coloring pages (ColorMode.BLACK_WHITE)
    """

    # Pricing (Google AI Studio - estimated)
    COST_PER_IMAGE = Decimal("0.04")  # $0.04 per image (estimated)

    def __init__(self, model: str | None = None):
        """Initialize Gemini provider.

        Args:
            model: Model to use (defaults to gemini-2.5-flash-image)
        """
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = model or "gemini-2.5-flash-image"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment")
        else:
            logger.info(f"GeminiImageProvider initialized: {self.model}")

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.api_key is not None

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization.

        Returns:
            False - Gemini generates raster images (PNG)
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
                message="Gemini provider not available",
                actionable_hint="Install google-genai: pip install google-genai",
                context={"provider": "gemini", "model": self.model},
            )

        # Use prompt directly from strategy (no duplication)
        # The strategy (e.g., ColoringBookStrategy) already builds the complete prompt
        full_prompt = prompt

        logger.info(f"Generating cover via Gemini (Nano Banana): {full_prompt[:100]}...")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Gemini API endpoint
                url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

                payload = {
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "response_modalities": ["IMAGE"],  # Image only output
                    },
                }

                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()

                # Extract image from response
                if "candidates" not in result or not result["candidates"]:
                    raise DomainError(
                        code=ErrorCode.PROVIDER_TIMEOUT,
                        message="No candidates in Gemini response",
                        actionable_hint="Check prompt and API quota",
                        context={"response": result},
                    )

                candidate = result["candidates"][0]
                if "content" not in candidate or "parts" not in candidate["content"]:
                    raise DomainError(
                        code=ErrorCode.PROVIDER_TIMEOUT,
                        message="No content parts in Gemini response",
                        actionable_hint="Check API response format",
                        context={"candidate": candidate},
                    )

                # Find inline image data
                image_data = None
                for part in candidate["content"]["parts"]:
                    if "inlineData" in part and part["inlineData"].get("mimeType") == "image/png":
                        image_data = part["inlineData"]["data"]
                        break

                if not image_data:
                    raise DomainError(
                        code=ErrorCode.PROVIDER_TIMEOUT,
                        message="No image data in Gemini response",
                        actionable_hint="Check API response format",
                        context={"parts": candidate["content"]["parts"]},
                    )

                # Decode base64 image
                image_bytes = base64.b64decode(image_data)

            # Resize to target dimensions if needed
            if spec.width_px or spec.height_px:
                img = Image.open(BytesIO(image_bytes))
                target_width = spec.width_px or img.width
                target_height = spec.height_px or img.height

                if (img.width, img.height) != (target_width, target_height):
                    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    image_bytes = buffer.getvalue()

            # Add rounded border for B&W coloring pages
            if spec.color_mode == ColorMode.BLACK_WHITE:
                logger.info("Adding rounded black border to coloring page...")
                image_bytes = self._add_rounded_border_to_image(image_bytes)

            logger.info(f"✅ Generated cover (Gemini Nano Banana): {len(image_bytes)} bytes")
            return image_bytes

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Gemini API error: {e.response.status_code} - {e.response.text}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Gemini API error: {e.response.status_code}",
                actionable_hint="Check API key and quota",
                context={"status": e.response.status_code, "response": e.response.text},
            ) from e

        except Exception as e:
            logger.error(f"❌ Gemini generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Gemini generation failed: {str(e)}",
                actionable_hint="Check API key, quota, and network",
                context={"provider": "gemini", "model": self.model, "error": str(e)},
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
        """Remove text from cover to create back cover.

        For Gemini, we just return the cover without text.
        The barcode space will be added later during KDP export assembly, not here.

        Args:
            cover_bytes: Original cover image (with text)
            barcode_width_inches: Unused (kept for interface compatibility)
            barcode_height_inches: Unused (kept for interface compatibility)
            barcode_margin_inches: Unused (kept for interface compatibility)

        Returns:
            Same image without text (barcode space will be added during KDP export)

        Raises:
            DomainError: If transformation fails
        """
        logger.info("🗑️  Removing text from cover (Gemini: returning cover as-is)...")

        # Just return the cover - barcode space will be added during KDP export
        # not during back cover generation
        logger.info(f"✅ Back cover ready (no barcode space): {len(cover_bytes)} bytes")
        return cover_bytes

    def _add_rounded_border_to_image(
        self,
        image_bytes: bytes,
        border_width: int = 5,
        corner_radius: int = 20,
        margin: int = 50,
    ) -> bytes:
        """Add a rounded black border to the image with white margin.

        Args:
            image_bytes: Original image bytes
            border_width: Width of the border in pixels (default: 5px)
            corner_radius: Radius for rounded corners in pixels (default: 20px)
            margin: White space between content and border in pixels (default: 50px)

        Returns:
            Image bytes with border and margin added
        """
        # Load image
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        orig_width, orig_height = img.size

        # Skip if image too small
        if orig_width < 100 or orig_height < 100:
            logger.warning(f"Image too small ({orig_width}x{orig_height}) for border, skipping")
            return image_bytes

        # Calculate new dimensions with margin
        total_padding = margin * 2
        new_width = orig_width
        new_height = orig_height

        # Create white background with padding
        bordered_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))

        # Shrink original image to leave margin
        content_width = new_width - total_padding
        content_height = new_height - total_padding
        img_resized = img.resize((content_width, content_height), Image.Resampling.LANCZOS)

        # Paste resized image centered with margin
        bordered_img.paste(img_resized, (margin, margin))

        # Draw the black rounded rectangle border
        draw = ImageDraw.Draw(bordered_img)
        draw.rounded_rectangle(
            (
                margin - border_width // 2,
                margin - border_width // 2,
                new_width - margin + border_width // 2 - 1,
                new_height - margin + border_width // 2 - 1,
            ),
            radius=corner_radius,
            outline=(0, 0, 0),
            width=border_width,
        )

        # Save and return
        buffer = BytesIO()
        bordered_img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _create_usage_metrics(self, model: str, num_images: int = 1) -> UsageMetrics:
        """Create usage metrics for Gemini response.

        Args:
            model: Model ID used
            num_images: Number of images generated

        Returns:
            UsageMetrics with cost calculation
        """
        total_cost = self.COST_PER_IMAGE * num_images

        logger.info(
            f"📊 Gemini usage (Nano Banana 🍌) - {model} | "
            f"Images: {num_images} | "
            f"Cost: ${total_cost:.6f}"
        )

        return UsageMetrics(
            model=model,
            prompt_tokens=0,  # Gemini doesn't expose token usage for images
            completion_tokens=0,
            cost=total_cost,
        )
