"""OpenRouter provider for image generation (Gemini 2.5 Flash Image Preview)."""

import base64
import logging
import os
from datetime import datetime
from io import BytesIO

import httpx
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
from backoffice.features.ebook.shared.infrastructure.utils.color_utils import (
    TEXT_BLACK_CMYK,
    convert_rgb_to_cmyk,
)
from backoffice.features.ebook.shared.infrastructure.utils.spine_generator import (
    get_font_path,
    load_font_safe,
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

    def __init__(
        self, model: str | None = None, track_usage_usecase=None, request_id: str | None = None
    ):
        """Initialize OpenRouter provider.

        Args:
            model: Specific model to use (defaults to Gemini 2.5 Flash Image Preview)
            track_usage_usecase: Optional TrackTokenUsageUseCase for cost tracking via events
            request_id: Optional request ID for cost tracking
        """
        from openai import AsyncOpenAI

        self.api_key = os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.track_usage_usecase = track_usage_usecase
        self.request_id = request_id
        self.client: AsyncOpenAI | None

        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info(f"OpenRouterImageProvider initialized: {self.model}")
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

        logger.info(f"Generating cover via OpenRouter: {full_prompt[:100]}...")

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

            # Track usage via events (new architecture)
            if response.usage and self.track_usage_usecase:
                await self._track_usage_from_response(response)

            # Extract image from response
            image_bytes = self._extract_image_from_response(response)

            # Resize to spec if needed
            if spec.width_px != 1024 or spec.height_px != 1024:
                image = Image.open(BytesIO(image_bytes))
                image = image.resize((spec.width_px, spec.height_px), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_bytes = buffer.getvalue()

            # Add rounded border for B&W coloring pages (programmatically, not via prompt)
            if spec.color_mode == ColorMode.BLACK_WHITE:
                logger.info("Adding rounded black border to coloring page...")
                image_bytes = self._add_rounded_border_to_image(image_bytes)

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
        """Remove text from cover to create back cover using Gemini vision.

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

            # Track usage via events (new architecture)
            if response.usage and self.track_usage_usecase:
                await self._track_usage_from_response(response)

            # Extract transformed image (without text)
            image_bytes = self._extract_image_from_response(response)
            logger.info(f"✅ Text removed by Gemini: {len(image_bytes)} bytes")

            # Step 2: Add barcode space programmatically with PIL
            logger.info("📦 Adding barcode space with PIL...")
            from io import BytesIO

            from PIL import Image, ImageDraw

            img = Image.open(BytesIO(image_bytes))
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

            draw.rectangle((x1, y1, x2, y2), fill=(255, 255, 255))

            # Convert back to bytes
            output = BytesIO()
            img.save(output, format="PNG")
            final_bytes = output.getvalue()

            logger.info(f"✅ Barcode space added: {len(final_bytes)} bytes")
            return final_bytes

        except Exception as e:
            logger.error(f"❌ Gemini transformation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Gemini vision transformation failed: {str(e)}",
                actionable_hint="Check if model supports image-to-image transformation",
                context={"provider": "openrouter", "model": self.model, "error": str(e)},
            ) from e

    def _download_image_sync(self, url: str) -> bytes:
        """Download image from URL synchronously.

        Args:
            url: URL to download from

        Returns:
            Image data as bytes
        """
        import asyncio

        async def download() -> bytes:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content

        result: bytes = asyncio.run(download())
        return result

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

        # Calculate new dimensions with margin
        # margin is the white space INSIDE the border
        total_padding = margin * 2  # margin on each side
        new_width = orig_width
        new_height = orig_height

        # Adjust values if image is too small (for testing with tiny images)
        if orig_width < 100 or orig_height < 100:
            logger.warning(f"Image too small ({orig_width}x{orig_height}) for border, skipping")
            return image_bytes

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

    async def generate_back_cover(
        self,
        back_config: BackCoverConfig,
        spec: ImageSpec,
        front_cover_bytes: bytes,
        front_cover_no_text_bytes: bytes,
        kdp_config: KDPExportConfig,
    ) -> bytes:
        """Generate KDP back cover with line art from cover + text.

        Args:
            back_config: Back cover configuration
            spec: Image specifications
            front_cover_bytes: Front cover for dominant color extraction
            front_cover_no_text_bytes: Front cover WITHOUT text for line art
            kdp_config: KDP export configuration

        Returns:
            CMYK TIFF back cover bytes at 300 DPI

        Raises:
            DomainError: If generation fails
        """
        # 1. Extract vibrant background color from front cover (not gray)
        from backoffice.features.ebook.shared.infrastructure.utils.color_utils import (
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

        # 3. Convert to CMYK BEFORE adding text
        bg_cmyk_bytes = convert_rgb_to_cmyk(
            bg_bytes, kdp_config.icc_rgb_profile, kdp_config.icc_cmyk_profile
        )

        # 4. Add text + barcode zone (on CMYK image)
        final_bytes = self._add_back_cover_text(bg_cmyk_bytes, back_config, spec, kdp_config)

        logger.info(f"✅ Generated back cover: {len(final_bytes)} bytes")
        return final_bytes

    # DEPRECATED: Back cover is now generated directly in coloring_book_strategy.py
    # This method is no longer used since we extract back cover from structure_json
    def _get_theme_primary_color(self, theme: str) -> tuple[int, int, int]:
        """Get primary color from theme palette.

        Args:
            theme: Theme name (e.g., 'pirates', 'unicorns')

        Returns:
            RGB tuple of the primary theme color
        """
        from pathlib import Path

        from backoffice.features.ebook.shared.domain.entities.theme_profile import (
            load_theme_from_yaml,
        )

        # Theme colors mapping with fallbacks
        theme_colors = {
            "pirates": (47, 79, 79),  # #2f4f4f - slate blue/gray
            "unicorns": (255, 182, 193),  # Pink
            "dinosaurs": (34, 139, 34),  # Forest green
        }

        # Try to load from YAML theme file
        try:
            themes_dir = Path(__file__).parent.parent.parent.parent / "themes"
            theme_file = themes_dir / f"{theme.lower()}.yml"

            if theme_file.exists():
                theme_profile = load_theme_from_yaml(theme_file)
                # Use first base color from palette
                hex_color = theme_profile.palette.base[0]
                # Convert hex to RGB
                hex_color = hex_color.lstrip("#")
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return (r, g, b)
        except Exception as e:
            logger.warning(f"Could not load theme palette for {theme}: {e}")

        # Fallback to hardcoded colors
        return theme_colors.get(theme.lower(), (135, 206, 235))  # Default sky blue

    # DEPRECATED: Back cover is now generated directly in coloring_book_strategy.py
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

            # Track usage via events (new architecture)
            if response.usage and self.track_usage_usecase:
                await self._track_usage_from_response(response)

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
        image_cmyk_bytes: bytes,
        back_config: BackCoverConfig,
        spec: ImageSpec,
        kdp_config: KDPExportConfig,
    ) -> bytes:
        """Add text and barcode zone to back cover CMYK image.

        Args:
            image_cmyk_bytes: CMYK background image
            back_config: Back cover configuration
            spec: Image specifications
            kdp_config: KDP export configuration

        Returns:
            CMYK TIFF with text and barcode zone
        """
        img = Image.open(BytesIO(image_cmyk_bytes))
        if img.mode != "CMYK":
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Image must be CMYK, got: {img.mode}",
                actionable_hint="Ensure CMYK conversion before text addition",
            )

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

        draw.text((x, y), text, fill=TEXT_BLACK_CMYK, font=title_font)

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
                fill=TEXT_BLACK_CMYK,
                font=copyright_font,
            )

        # 3. Barcode zone (pure white CMYK, in TRIM)
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
            fill=(0, 0, 0, 0),  # White in CMYK
        )

        # Save with DPI
        buffer = BytesIO()
        img.save(buffer, format="TIFF", compression="tiff_adobe_deflate", dpi=(300, 300))
        return buffer.getvalue()

    async def _track_usage_from_response(self, response) -> None:
        """Extract usage from OpenRouter response and emit tracking event.

        Args:
            response: OpenRouter API response with usage data
        """
        from decimal import Decimal

        if not response.usage:
            logger.warning("⚠️ No usage data in OpenRouter response")
            return

        usage_data = response.usage
        prompt_tokens = usage_data.prompt_tokens or 0
        completion_tokens = usage_data.completion_tokens or 0

        # Try to get REAL cost from OpenRouter (includes platform fees)
        real_cost = Decimal("0")
        if hasattr(usage_data, "cost") and usage_data.cost is not None:
            real_cost = Decimal(str(usage_data.cost))
            logger.info(f"💰 OpenRouter real cost: ${real_cost} (includes platform fees)")
        else:
            logger.warning("⚠️ OpenRouter didn't provide cost - using $0.00")

        # Track usage via use case (emits events)
        await self.track_usage_usecase.execute(
            request_id=self.request_id or "unknown",
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=real_cost,
        )

        logger.info(
            f"📊 Tracked - {self.model} | "
            f"Prompt: {prompt_tokens} | "
            f"Completion: {completion_tokens} | "
            f"Cost: ${real_cost}"
        )
