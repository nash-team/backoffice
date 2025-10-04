"""Replicate provider for image generation (flux-schnell)."""

import base64
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


class ReplicateImageProvider(CoverGenerationPort, ContentPageGenerationPort):
    """Replicate provider for covers and pages using flux-schnell.

    Model: black-forest-labs/flux-schnell
    Cost: $0.003/image (333 images for $1)
    Speed: ~0.8s generation time

    Supports both:
    - Colorful covers (ColorMode.COLOR)
    - B&W coloring pages (ColorMode.BLACK_WHITE)
    """

    # Model configurations
    FLUX_SCHNELL = "black-forest-labs/flux-schnell"
    FLUX_DEV_PRUNA = (
        "prunaai/flux.1-dev:b0306d92aa025bb747dc74162f3c27d6ed83798e08e5f8977adf3d859d0536a3"
    )
    TEXT_REMOVAL = "flux-kontext-apps/text-removal"

    # Pricing per image (in USD)
    PRICING = {
        FLUX_SCHNELL: Decimal("0.003"),  # $3 per 1000 images
        FLUX_DEV_PRUNA: Decimal("0.02"),  # Estimated ~$0.02 per image
        TEXT_REMOVAL: Decimal("0.04"),  # $0.04 per image (official pricing)
    }

    def __init__(self, model: str | None = None, token_tracker=None):
        """Initialize Replicate provider.

        Args:
            model: Specific model to use (defaults to flux-schnell)
            token_tracker: Optional TokenTracker for cost tracking
        """
        self.api_token = os.getenv("REPLICATE_API_TOKEN")
        self.model = model or self.FLUX_SCHNELL
        self.token_tracker = token_tracker

        self.client: replicate.Client | None = None

        if self.api_token:
            try:
                import replicate

                self.client = replicate.Client(api_token=self.api_token)
                logger.info(f"ReplicateImageProvider initialized: {self.model}")
            except ImportError as e:
                logger.error("replicate package not installed: pip install replicate")
                raise DomainError(
                    code=ErrorCode.MODEL_UNAVAILABLE,
                    message="Replicate package not installed",
                    actionable_hint="Run: pip install replicate",
                    context={"error": str(e)},
                ) from e
        else:
            logger.warning("REPLICATE_API_TOKEN not found")

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.client is not None

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization.

        Returns:
            False - Replicate generates raster images (PNG/WebP)
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
                message="Replicate provider not available",
                actionable_hint="Configure REPLICATE_API_TOKEN in .env",
                context={"provider": "replicate", "model": self.model},
            )

        # Build prompt based on color mode
        if spec.color_mode == ColorMode.BLACK_WHITE:
            # B&W coloring page style - STRONG keywords for FLUX
            full_prompt = (
                f"COLORING BOOK PAGE: Black and white line drawing, outline only, "
                f"simple linework, thick black outlines on pure white background. "
                f"NO COLORS, NO SHADING, NO GRADIENTS - just clean black lines. "
                f"Line art style, coloring page for kids, simple shapes to color in. "
                f"Subject: {prompt}"
            )
        else:
            # Colorful cover style - Children's book illustration (NO TEXT)
            full_prompt = (
                f"Children's book cover illustration, {prompt}. "
                f"Colorful, friendly, engaging for kids age 3-8. "
                f"NO text, NO words, NO letters on the image. "
                f"Professional digital art, vibrant colors, cheerful atmosphere."
            )

        logger.info(f"Generating cover via Replicate: {full_prompt[:100]}...")

        try:
            # Calculate aspect ratio for Replicate
            aspect_ratio = f"{spec.width_px}:{spec.height_px}"
            if spec.width_px == spec.height_px:
                aspect_ratio = "1:1"

            # Choose model based on color mode
            if spec.color_mode == ColorMode.COLOR:
                # TEST: Use FLUX.1-dev (PrunaAI) for better quality covers
                model_to_use = self.FLUX_DEV_PRUNA
                input_params = {
                    "seed": seed if seed is not None else -1,
                    "prompt": full_prompt,
                    "guidance": 3.5,
                    "image_size": spec.width_px,
                    "speed_mode": "Extra Juiced 🔥 (more speed)",
                    "aspect_ratio": aspect_ratio,
                    "output_format": "jpg",
                    "output_quality": 80,
                    "num_inference_steps": 28,
                }
            else:
                # Use flux-schnell for B&W pages (cheaper and faster)
                model_to_use = self.model
                input_params = {
                    "prompt": full_prompt,
                    "aspect_ratio": aspect_ratio,
                    "num_outputs": 1,
                    "output_format": "png",
                    "output_quality": 95,
                    "num_inference_steps": 4,
                    "go_fast": True,
                    "megapixels": "1",
                }
                if seed is not None:
                    input_params["seed"] = seed

            assert self.client is not None  # is_available() check ensures this
            output = self.client.run(model_to_use, input=input_params)

            # Extract image bytes from output (format varies by model)
            raw_bytes: bytes
            if isinstance(output, list) and len(output) > 0:
                # List format (flux-schnell)
                raw_bytes = output[0].read()
            elif hasattr(output, "read"):
                # Single FileOutput format (flux.1-dev)
                raw_bytes = output.read()
            else:
                raise ValueError(f"Unexpected output format: {type(output)}")

            # Resize to exact spec if needed
            img = Image.open(BytesIO(raw_bytes))
            result_bytes: bytes
            if img.size != (spec.width_px, spec.height_px):
                resized = img.resize((spec.width_px, spec.height_px), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                resized.save(buffer, format="PNG")
                result_bytes = buffer.getvalue()
            else:
                result_bytes = raw_bytes

            # Add rounded border for B&W coloring pages
            if spec.color_mode == ColorMode.BLACK_WHITE:
                logger.info("Adding rounded black border to coloring page...")
                result_bytes = self._add_rounded_border_to_image(result_bytes)

            # Track usage with cost
            if self.token_tracker:
                usage_metrics = self._create_usage_metrics(model_to_use, num_images=1)
                await self.token_tracker.add_usage_metrics(usage_metrics)

            logger.info(f"✅ Generated cover: {len(result_bytes)} bytes")
            return result_bytes

        except Exception as e:
            logger.error(f"❌ Replicate generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Replicate generation failed: {str(e)}",
                actionable_hint="Check REPLICATE_API_TOKEN validity and model availability",
                context={"provider": "replicate", "model": self.model, "error": str(e)},
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
        """Remove text from cover to create back cover using text removal model.

        Args:
            cover_bytes: Original cover image (with text)

        Returns:
            Same image without text (for back cover)

        Raises:
            DomainError: If transformation fails
        """
        if not self.is_available():
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="Replicate provider not available",
                actionable_hint="Configure REPLICATE_API_TOKEN in .env",
                context={"provider": "replicate"},
            )

        logger.info("🗑️  Removing text from cover with Replicate text-removal model...")

        try:
            # Convert to base64 data URL for upload
            image_b64 = base64.b64encode(cover_bytes).decode("utf-8")
            data_url = f"data:image/png;base64,{image_b64}"

            # Run text removal model
            assert self.client is not None  # is_available() check ensures this
            output = self.client.run(
                self.TEXT_REMOVAL,
                input={
                    "input_image": data_url,
                    "aspect_ratio": "match_input_image",
                    "output_format": "png",
                },
            )

            # Extract result
            result_bytes: bytes
            if isinstance(output, list) and len(output) > 0:
                result_bytes = output[0].read()
            elif hasattr(output, "read"):
                result_bytes = output.read()
            else:
                raise ValueError(f"Unexpected output format: {type(output)}")

            # Track usage
            if self.token_tracker:
                usage_metrics = self._create_usage_metrics(self.TEXT_REMOVAL, num_images=1)
                await self.token_tracker.add_usage_metrics(usage_metrics)

            logger.info(f"✅ Text removed: {len(result_bytes)} bytes")

            # Add barcode space programmatically with PIL
            logger.info("📦 Adding barcode space with PIL...")
            img = Image.open(BytesIO(result_bytes))
            from PIL import ImageDraw

            draw = ImageDraw.Draw(img)

            w, h = img.size
            rect_w = int(w * 0.15)  # 15% width
            rect_h = int(h * 0.08)  # 8% height
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

            logger.info(f"✅ Barcode space added: {len(final_bytes)} bytes")
            return final_bytes

        except Exception as e:
            logger.error(f"❌ Replicate text removal failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Replicate text removal failed: {str(e)}",
                actionable_hint="Check if text-removal model is available",
                context={"provider": "replicate", "error": str(e)},
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
        """Create usage metrics for Replicate response.

        Replicate doesn't provide token usage, so we create minimal metrics
        with only cost tracking based on per-image pricing.

        Args:
            model: Model ID used
            num_images: Number of images generated

        Returns:
            UsageMetrics with cost
        """
        # Get cost per image from pricing table
        cost_per_image = self.PRICING.get(model, Decimal("0"))
        total_cost = cost_per_image * num_images

        logger.info(
            f"📊 Replicate usage - {model} | "
            f"Images: {num_images} | "
            f"Cost: ${total_cost:.6f} "
            f"(${cost_per_image}/image)"
        )

        return UsageMetrics(
            model=model,
            prompt_tokens=0,  # Replicate doesn't expose token usage
            completion_tokens=0,
            cost=total_cost,
        )
