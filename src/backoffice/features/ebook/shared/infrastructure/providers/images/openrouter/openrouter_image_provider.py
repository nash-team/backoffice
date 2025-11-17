"""OpenRouter provider for image generation (Gemini 2.5 Flash Image Preview)."""

import base64
import logging
import os
from datetime import datetime
from io import BytesIO

from PIL import Image, ImageDraw

from backoffice.features.ebook.shared.domain.entities.ebook import (
    BackCoverConfig,
    KDPExportConfig,
    inches_to_px,
)
from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.ebook.shared.infrastructure.providers.images.openrouter.response_extractor import (
    OpenRouterResponseExtractor,
)
from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.color_utils import (
    TEXT_BLACK_RGB,
)
from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.spine_generator import (
    get_font_path,
    load_font_safe,
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

    async def generate_back_cover(
        self,
        back_config: BackCoverConfig,
        spec: ImageSpec,
        front_cover_bytes: bytes,
        front_cover_no_text_bytes: bytes,
        kdp_config: KDPExportConfig,
    ) -> bytes:
        """Generate KDP back cover with line art from cover + text.

        DEPRECATED: Back cover is now generated directly in coloring_book_strategy.py
        using Gemini Vision text removal. This method is kept for backward compatibility.

        IMPORTANT: KDP requires RGB, not CMYK!

        Args:
            back_config: Back cover configuration
            spec: Image specifications
            front_cover_bytes: Front cover for dominant color extraction
            front_cover_no_text_bytes: Front cover WITHOUT text for line art
            kdp_config: KDP export configuration (icc profiles are now ignored)

        Returns:
            RGB PNG back cover bytes at 300 DPI

        Raises:
            DomainError: If generation fails
        """
        # 1. Extract vibrant background color from front cover (not gray)
        from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.color_utils import (
            extract_dominant_color_exact,
        )

        background_color = extract_dominant_color_exact(front_cover_bytes)
        logger.info(f"Extracted background color from cover: RGB{background_color}")

        # 2. Create line art from cover WITHOUT text
        # This creates the "coloring book preview" effect on the back cover
        logger.info("Creating line art from cover without text...")
        bg_bytes = self._create_outline_back_cover(
            front_cover_bytes=front_cover_no_text_bytes,
            width=spec.width_px,
            height=spec.height_px,
            background_color=background_color,
        )

        # 3. Add text + barcode zone (on RGB image - KDP requirement)
        final_bytes = self._add_back_cover_text(bg_bytes, back_config, spec, kdp_config)

        logger.info(f"✅ Generated back cover: {len(final_bytes)} bytes")
        return final_bytes

    # This method is no longer used since we extract back cover from structure_json
    async def _generate_line_art_back_cover(
        self,
        back_config: BackCoverConfig,
        spec: ImageSpec,
        background_color: tuple[int, int, int],
    ) -> bytes:
        """Generate line art back cover using AI with colored background.

        Args:
            back_config: Back cover configuration
            spec: Image specification
            background_color: RGB background color extracted from front cover

        Returns:
            PNG image with AI-generated line art on colored background
        """
        if not self.is_available():
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="OpenRouter provider not available",
                actionable_hint="Configure LLM_API_KEY in .env",
            )

        # Convert RGB to hex for prompt
        bg_hex = "#{:02x}{:02x}{:02x}".format(*background_color)
        logger.info(f"Generating line art with background color: {bg_hex}")

        # Build prompt for line art generation
        theme = back_config.theme.lower()
        full_prompt = (
            f"Create a simple line art illustration for a {theme} coloring book back cover.\n"
            f"STYLE REQUIREMENTS:\n"
            f"- BLACK LINE ART ONLY (like a coloring book outline)\n"
            f"- Background color: {bg_hex} (RGB{background_color})\n"
            f"- Clean, thick black lines (2-3px)\n"
            f"- NO interior shading, NO gradients, NO additional colors\n"
            f"- Simple, centered composition\n"
            f"- Simpler than front cover (this is the back)\n"
            f"- Fill entire frame edge-to-edge\n\n"
            f"Theme: {theme.capitalize()}"
        )

        logger.info("Generating line art back cover via OpenRouter...")

        try:
            # Generate via chat endpoint (Gemini approach)
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
                temperature=0.7,
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

            logger.info(f"✅ Generated line art back cover: {len(image_bytes)} bytes")
            return image_bytes

        except Exception as e:
            logger.error(f"❌ Line art back cover generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Line art generation failed: {str(e)}",
                actionable_hint="Check LLM_API_KEY validity",
                context={"error": str(e)},
            ) from e

    # DEPRECATED: Back cover is now generated directly in coloring_book_strategy.py
    # This method is no longer used since we extract back cover from structure_json
    def _create_outline_back_cover(
        self,
        front_cover_bytes: bytes,
        width: int,
        height: int,
        background_color: tuple[int, int, int],
    ) -> bytes:
        """Create back cover with outline/line art version of front cover.

        Args:
            front_cover_bytes: Front cover image bytes
            width: Target width
            height: Target height
            background_color: RGB background color

        Returns:
            PNG image with line art on colored background
        """
        from PIL import ImageFilter, ImageOps

        # Load front cover
        cover = Image.open(BytesIO(front_cover_bytes)).convert("RGB")

        # Resize to target dimensions
        cover = cover.resize((width, height), Image.Resampling.LANCZOS)

        # Create colored background first
        final = Image.new("RGB", (width, height), background_color)

        # Convert cover to grayscale
        gray = cover.convert("L")

        # Apply multiple edge detection for better results
        edges1 = gray.filter(ImageFilter.FIND_EDGES)
        edges2 = gray.filter(ImageFilter.CONTOUR)

        # Combine both edge detections
        from PIL import ImageChops

        edges = ImageChops.darker(edges1, edges2)

        # Enhance contrast dramatically
        edges = ImageOps.autocontrast(edges, cutoff=10)

        # Apply multiple threshold passes for cleaner lines
        # First pass: get strong edges
        edges = edges.point(lambda x: 0 if x > 40 else 255)

        # Apply morphological operations to clean up lines
        edges = edges.filter(ImageFilter.MinFilter(3))  # Remove noise
        edges = edges.filter(ImageFilter.MaxFilter(3))  # Thicken lines slightly

        # Final threshold for pure black/white
        edges = edges.point(lambda x: 0 if x < 128 else 255, mode="1")

        # Convert to RGB (black lines)
        edges_rgb = edges.convert("RGB")

        # Composite onto colored background
        # Where edges are black (0,0,0), draw black lines
        # Where edges are white (255,255,255), keep background color
        import numpy as np

        # Use numpy for faster pixel manipulation
        edges_array = np.array(edges_rgb)
        final_array = np.array(final)

        # Where edges are black (all channels = 0), keep black
        # Otherwise use background color
        mask = edges_array[:, :, 0] == 0
        final_array[mask] = [0, 0, 0]

        final = Image.fromarray(final_array)

        # Save as PNG
        buffer = BytesIO()
        final.save(buffer, format="PNG")
        return buffer.getvalue()

    def _create_simple_gradient(
        self, width: int, height: int, base_color: tuple[int, int, int]
    ) -> bytes:
        """Create a subtle gradient background for back cover.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            base_color: Base RGB color extracted from front cover

        Returns:
            PNG image bytes with subtle gradient
        """
        from PIL import ImageDraw

        # Create new RGB image
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        r, g, b = base_color

        # Create a subtle vertical gradient (darker at top, lighter at bottom)
        for y in range(height):
            # Subtle darkening at top (10% darker), lightening at bottom (15% lighter)
            progress = y / height
            if progress < 0.5:
                # Top half: darken slightly
                factor = 0.9 + (progress * 0.2)  # 0.9 to 1.0
            else:
                # Bottom half: lighten slightly
                factor = 1.0 + ((progress - 0.5) * 0.3)  # 1.0 to 1.15

            r_y = min(255, int(r * factor))
            g_y = min(255, int(g * factor))
            b_y = min(255, int(b * factor))

            draw.line([(0, y), (width, y)], fill=(r_y, g_y, b_y))

        # Save as PNG
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _add_back_cover_text(
        self,
        image_rgb_bytes: bytes,
        back_config: BackCoverConfig,
        spec: ImageSpec,
        kdp_config: KDPExportConfig,
    ) -> bytes:
        """Add text and barcode zone to back cover RGB image.

        IMPORTANT: KDP requires RGB, not CMYK!

        Args:
            image_rgb_bytes: RGB background image
            back_config: Back cover configuration
            spec: Image specifications
            kdp_config: KDP export configuration

        Returns:
            RGB PNG with text and barcode zone
        """
        from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.color_utils import (
            ensure_rgb,
        )

        img = Image.open(BytesIO(image_rgb_bytes))
        # Ensure RGB mode (KDP requirement)
        img = ensure_rgb(img)

        draw = ImageDraw.Draw(img)

        # Load fonts with fallback
        title_font = load_font_safe(get_font_path("PlayfairDisplay-Bold.ttf"), 48)
        copyright_font = load_font_safe(get_font_path("Lato-Regular.ttf"), 16)

        # Dimensions
        trim_width_px = inches_to_px(kdp_config.trim_size[0])
        trim_height_px = inches_to_px(kdp_config.trim_size[1])
        bleed_px = inches_to_px(kdp_config.bleed_size)

        # 1. Main title centered (K 100%)
        text = f"Coloring by {back_config.author_name}"
        bbox = draw.textbbox((0, 0), text, font=title_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (img.width - text_width) // 2
        y = (img.height - text_height) // 2

        draw.text((x, y), text, fill=TEXT_BLACK_RGB, font=title_font)

        # 2. Copyright (bottom left, in TRIM)
        if back_config.include_copyright:
            year = back_config.copyright_year or datetime.now().year
            copyright_text = f"© {year} {back_config.author_name}"

            margin_px = inches_to_px(0.25)

            # ✅ Subtract text height
            c_bbox = draw.textbbox((0, 0), copyright_text, font=copyright_font)
            ch = c_bbox[3] - c_bbox[1]

            copyright_x = bleed_px + margin_px
            copyright_y = img.height - bleed_px - margin_px - ch

            draw.text(
                (copyright_x, copyright_y),
                copyright_text,
                fill=TEXT_BLACK_RGB,
                font=copyright_font,
            )

        # 3. Barcode zone (pure white RGB, in TRIM)
        BARCODE_WIDTH = inches_to_px(2.0)
        BARCODE_HEIGHT = inches_to_px(1.2)
        QUIET_ZONE = inches_to_px(0.125)
        MARGIN_TRIM = inches_to_px(0.25)

        # Position in trim
        x_trim = trim_width_px - BARCODE_WIDTH - MARGIN_TRIM
        y_trim = trim_height_px - BARCODE_HEIGHT - MARGIN_TRIM

        # Translate with bleed
        barcode_x = bleed_px + x_trim
        barcode_y = bleed_px + y_trim

        # White rectangle (0,0,0,0 in CMYK = white)
        draw.rectangle(
            (
                barcode_x - QUIET_ZONE,
                barcode_y - QUIET_ZONE,
                barcode_x + BARCODE_WIDTH + QUIET_ZONE,
                barcode_y + BARCODE_HEIGHT + QUIET_ZONE,
            ),
            fill=(255, 255, 255),  # White in RGB
        )

        # Save with DPI (PNG format for RGB - KDP requirement)
        buffer = BytesIO()
        img.save(buffer, format="PNG", dpi=(300, 300))
        return buffer.getvalue()
