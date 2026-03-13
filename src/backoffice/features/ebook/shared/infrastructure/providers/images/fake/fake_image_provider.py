"""Fake image provider for local testing without GPU or API keys.

Generates placeholder images with Pillow at small size then resizes to target.
Instant, zero cost, perfect for testing the full UI flow.
Emits progress events so the WebSocket UI works identically to real providers.
"""

import asyncio
import io
import logging
import random

from PIL import Image, ImageDraw, ImageFont

from backoffice.features.ebook.regeneration.domain.events.content_page_regenerating_status_event import (
    ContentPageRegeneratingStatusEvent,
)
from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec
from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.ebook.shared.domain.ports.image_edit_port import ImageEditPort
from backoffice.features.shared.infrastructure.events.event_bus_singleton import get_event_bus

logger = logging.getLogger(__name__)

# Simulated generation steps and delay between them
_FAKE_TOTAL_STEPS = 5
_FAKE_STEP_DELAY = 0.3  # seconds

# Generate at this size, then resize to target (fast)
_RENDER_WIDTH = 400
_RENDER_HEIGHT = 500


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=size)
    except (OSError, IOError):
        return ImageFont.load_default()


class FakeImageProvider(CoverGenerationPort, ContentPageGenerationPort, ImageEditPort):
    """Placeholder image provider for testing the full ebook generation flow.

    Generates at a small resolution then resizes to target spec (like real
    providers that generate at model resolution then resize for KDP).
    """

    def __init__(self, model: str = "fake") -> None:
        self.model = model
        self.event_bus = get_event_bus()
        logger.info("FakeImageProvider initialized (zero cost, instant)")

    async def _emit_progress(self, spec: ImageSpec) -> None:
        """Simulate generation progress so the WebSocket UI shows a progress bar."""
        if not spec.ebook_id or spec.page_index is None:
            return
        for step in range(_FAKE_TOTAL_STEPS):
            status = step * 100 // _FAKE_TOTAL_STEPS
            await self.event_bus.publish(
                ContentPageRegeneratingStatusEvent(
                    ebook_id=spec.ebook_id,
                    page_index=spec.page_index,
                    status=status,
                    state="running",
                    nb_total_steps=_FAKE_TOTAL_STEPS,
                    current_step=step,
                )
            )
            await asyncio.sleep(_FAKE_STEP_DELAY)
        # Final "finished" event
        await self.event_bus.publish(
            ContentPageRegeneratingStatusEvent(
                ebook_id=spec.ebook_id,
                page_index=spec.page_index,
                status=100,
                state="finished",
                nb_total_steps=_FAKE_TOTAL_STEPS,
                current_step=_FAKE_TOTAL_STEPS,
            )
        )

    def is_available(self) -> bool:
        return True

    def supports_vectorization(self) -> bool:
        return False

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Generate a colorful placeholder cover (gradient + title)."""
        logger.info(f"[FAKE] Generating cover: {prompt[:60]}...")
        await self._emit_progress(spec)
        rng = random.Random(seed or random.randint(0, 99999))

        w, h = _RENDER_WIDTH, _RENDER_HEIGHT
        img = Image.new("RGB", (w, h))

        # Fast gradient via line-by-line drawing
        draw = ImageDraw.Draw(img)
        hue = rng.randint(0, 200)
        for y in range(h):
            r = (hue + y * 180 // h) % 256
            g = (100 + y * 155 // h) % 256
            b = (hue + 80) % 256
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        # Title
        font = _load_font(w // 12)
        title = prompt[:35] + "..." if len(prompt) > 35 else prompt
        bbox = draw.textbbox((0, 0), title, font=font)
        tx = (w - (bbox[2] - bbox[0])) // 2
        ty = h // 3
        draw.text((tx + 1, ty + 1), title, fill=(0, 0, 0), font=font)
        draw.text((tx, ty), title, fill=(255, 255, 255), font=font)

        # Watermark
        small_font = _load_font(w // 20)
        draw.text((8, h - 25), "FAKE PREVIEW", fill=(255, 255, 255), font=small_font)

        # Resize to target KDP spec
        img = img.resize((spec.width_px, spec.height_px), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def generate_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Generate a placeholder coloring page with geometric shapes."""
        logger.info(f"[FAKE] Generating page: {prompt[:60]}...")
        await self._emit_progress(spec)
        rng = random.Random(seed or random.randint(0, 99999))

        w, h = _RENDER_WIDTH, _RENDER_HEIGHT
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)

        # Random geometric shapes (line-art style)
        for _ in range(rng.randint(8, 20)):
            shape = rng.choice(["circle", "rect", "line", "polygon"])
            x1, y1 = rng.randint(30, w - 30), rng.randint(30, h - 30)

            if shape == "circle":
                r = rng.randint(20, min(w, h) // 4)
                draw.ellipse((x1 - r, y1 - r, x1 + r, y1 + r), outline="black", width=2)
            elif shape == "rect":
                rw, rh = rng.randint(30, w // 3), rng.randint(30, h // 3)
                draw.rectangle((x1, y1, x1 + rw, y1 + rh), outline="black", width=2)
            elif shape == "line":
                x2, y2 = rng.randint(30, w - 30), rng.randint(30, h - 30)
                draw.line((x1, y1, x2, y2), fill="black", width=2)
            elif shape == "polygon":
                pts = [(rng.randint(30, w - 30), rng.randint(30, h - 30)) for _ in range(rng.randint(3, 6))]
                draw.polygon(pts, outline="black", width=2)

        # Label
        font = _load_font(w // 18)
        label = prompt[:40] + "..." if len(prompt) > 40 else prompt
        draw.text((15, 15), label, fill=(180, 180, 180), font=font)
        draw.text((15, h - 30), "FAKE", fill=(200, 200, 200), font=font)

        # Resize to target KDP spec
        img = img.resize((spec.width_px, spec.height_px), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def remove_text_from_cover(
        self,
        image_bytes: bytes,
        spec: ImageSpec,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.2,
        barcode_margin_inches: float = 0.25,
    ) -> bytes:
        """Return cover as-is for fake back cover."""
        return image_bytes

    async def edit_image(
        self,
        image_bytes: bytes,
        edit_prompt: str,
        spec: ImageSpec,
    ) -> bytes:
        """Return image with an 'EDITED' overlay."""
        logger.info(f"[FAKE] Editing image: {edit_prompt[:60]}...")
        await self._emit_progress(spec)
        img = Image.open(io.BytesIO(image_bytes))
        draw = ImageDraw.Draw(img)
        font = _load_font(img.width // 15)
        draw.text((10, 10), f"EDITED: {edit_prompt[:30]}", fill=(255, 0, 0), font=font)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
