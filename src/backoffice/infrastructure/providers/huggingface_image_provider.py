"""Hugging Face provider for image generation (FREE tier with Inference API)."""

import logging
import os
from decimal import Decimal
from io import BytesIO

from PIL import Image

from backoffice.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.domain.ports.content_page_generation_port import ContentPageGenerationPort
from backoffice.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.domain.value_objects.usage_metrics import UsageMetrics

logger = logging.getLogger(__name__)


class HuggingFaceImageProvider(CoverGenerationPort, ContentPageGenerationPort):
    """Hugging Face provider for covers and pages using Inference API.

    Model: black-forest-labs/FLUX.1-schnell (FREE)
    Cost: $0 (with rate limits: ~1 req/sec, 1000 req/day)
    Speed: ~3-5s generation time

    Supports both:
    - Colorful covers (ColorMode.COLOR)
    - B&W coloring pages (ColorMode.BLACK_WHITE)
    """

    # Model configurations
    FLUX_SCHNELL = "black-forest-labs/FLUX.1-schnell"
    SDXL = "stabilityai/stable-diffusion-xl-base-1.0"

    # Cost: FREE (rate limited)
    COST_PER_IMAGE = Decimal("0")  # Gratuit!

    def __init__(self, model: str | None = None, token_tracker=None):
        """Initialize Hugging Face provider.

        Args:
            model: Specific model to use (defaults to FLUX.1-schnell)
            token_tracker: Optional TokenTracker for cost tracking
        """
        # Support both HF_API_TOKEN and HF_TOKEN (common aliases)
        self.api_token = os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN")
        self.model = model or self.FLUX_SCHNELL
        self.token_tracker = token_tracker

        self.client: InferenceClient | None = None

        if self.api_token:
            try:
                from huggingface_hub import InferenceClient

                self.client = InferenceClient(token=self.api_token)
                logger.info(f"HuggingFaceImageProvider initialized: {self.model}")
            except ImportError as e:
                logger.error("huggingface_hub package not installed: pip install huggingface-hub")
                raise DomainError(
                    code=ErrorCode.MODEL_UNAVAILABLE,
                    message="Hugging Face package not installed",
                    actionable_hint="Run: pip install huggingface-hub",
                    context={"error": str(e)},
                ) from e
        else:
            logger.warning("HF_API_TOKEN not found")

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.client is not None

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization.

        Returns:
            False - Hugging Face generates raster images (PNG)
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
                message="Hugging Face provider not available",
                actionable_hint="Configure HF_API_TOKEN or HF_TOKEN in .env (get free token at https://huggingface.co/settings/tokens)",
                context={"provider": "huggingface", "model": self.model},
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

        logger.info(f"Generating cover via Hugging Face (FREE): {full_prompt[:100]}...")

        try:
            assert self.client is not None  # is_available() check ensures this

            # Generate image using Hugging Face Inference API
            # Note: text_to_image returns PIL Image
            # FLUX.1-schnell is optimized for 4-8 steps (max 16 on HF free tier)
            pil_image = self.client.text_to_image(
                prompt=full_prompt,
                model=self.model,
                # Hugging Face params (limited to max 16 steps on free tier)
                guidance_scale=7.5,
                num_inference_steps=4 if seed is None else 8,
                # Note: seed might not be supported by all models
            )

            # Resize to exact spec
            if pil_image.size != (spec.width_px, spec.height_px):
                pil_image = pil_image.resize(
                    (spec.width_px, spec.height_px), Image.Resampling.LANCZOS
                )

            # Convert to bytes
            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            result_bytes = buffer.getvalue()

            # Add rounded border for B&W coloring pages
            if spec.color_mode == ColorMode.BLACK_WHITE:
                logger.info("Adding rounded black border to coloring page...")
                result_bytes = self._add_rounded_border_to_image(result_bytes)

            # Track usage (FREE = $0 cost)
            if self.token_tracker:
                usage_metrics = self._create_usage_metrics(self.model, num_images=1)
                await self.token_tracker.add_usage_metrics(usage_metrics)

            logger.info(f"✅ Generated cover (FREE): {len(result_bytes)} bytes")
            return result_bytes

        except Exception as e:
            logger.error(f"❌ Hugging Face generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Hugging Face generation failed: {str(e)}",
                actionable_hint="Check HF_API_TOKEN validity and rate limits (~1 req/sec, 1000/day)",
                context={"provider": "huggingface", "model": self.model, "error": str(e)},
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
    ) -> bytes:
        """Remove text from cover to create back cover.

        Note: Hugging Face Inference API doesn't have a direct text removal model.
        We'll use a simple PIL-based solution (blur text areas) or return as-is.

        Args:
            cover_bytes: Original cover image (with text)

        Returns:
            Same image without text (for back cover)

        Raises:
            DomainError: If transformation fails
        """
        logger.info("🗑️  Removing text from cover (HF: PIL-based fallback)...")

        try:
            # Simple fallback: return image as-is with barcode space
            # (HF doesn't have a free text removal model)

            # Add barcode space programmatically with PIL
            logger.info("📦 Adding barcode space with PIL...")
            img = Image.open(BytesIO(cover_bytes))
            from PIL import ImageDraw

            draw = ImageDraw.Draw(img)

            w, h = img.size
            rect_w = int(w * 0.15)  # 15% width
            rect_h = int(w * 0.08)  # 8% height
            margin = int(w * 0.02)  # 2% margin

            # Bottom-right white rectangle
            x1 = w - rect_w - margin
            y1 = h - rect_h - margin
            x2 = w - margin
            y2 = h - margin

            draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255))

            # Convert back to bytes
            output_buffer = BytesIO()
            img.save(output_buffer, format="PNG")
            final_bytes = output_buffer.getvalue()

            # Track usage (FREE)
            if self.token_tracker:
                usage_metrics = self._create_usage_metrics(
                    self.model + "-text-removal", num_images=0
                )
                await self.token_tracker.add_usage_metrics(usage_metrics)

            logger.info(f"✅ Barcode space added (FREE): {len(final_bytes)} bytes")
            return final_bytes

        except Exception as e:
            logger.error(f"❌ Hugging Face text removal failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Hugging Face text removal failed: {str(e)}",
                actionable_hint="Check image format",
                context={"provider": "huggingface", "error": str(e)},
            ) from e

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
        from PIL import ImageDraw

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
            [
                (margin - border_width // 2, margin - border_width // 2),
                (
                    new_width - margin + border_width // 2 - 1,
                    new_height - margin + border_width // 2 - 1,
                ),
            ],
            radius=corner_radius,
            outline=(0, 0, 0),
            width=border_width,
        )

        # Save and return
        buffer = BytesIO()
        bordered_img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _create_usage_metrics(self, model: str, num_images: int = 1) -> UsageMetrics:
        """Create usage metrics for Hugging Face response.

        Hugging Face Inference API is FREE (with rate limits).

        Args:
            model: Model ID used
            num_images: Number of images generated

        Returns:
            UsageMetrics with cost = $0
        """
        total_cost = self.COST_PER_IMAGE * num_images

        logger.info(
            f"📊 Hugging Face usage (FREE) - {model} | "
            f"Images: {num_images} | "
            f"Cost: ${total_cost:.6f} 🎉"
        )

        return UsageMetrics(
            model=model,
            prompt_tokens=0,  # HF doesn't expose token usage
            completion_tokens=0,
            cost=total_cost,
        )
