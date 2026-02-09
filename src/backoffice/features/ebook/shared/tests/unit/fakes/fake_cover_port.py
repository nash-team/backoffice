"""Fake cover generation port for testing."""

import io

from PIL import Image

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort

_FAKE_PNG_CACHE: bytes | None = None


def _make_fake_png(width: int = 500, height: int = 500) -> bytes:
    """Create a valid PNG image for testing (> 1KB to pass quality validation).

    Uses a gradient pattern to ensure the PNG compresses to > 1KB.
    Cached to avoid regenerating on every call.
    """
    global _FAKE_PNG_CACHE  # noqa: PLW0603
    if _FAKE_PNG_CACHE is not None:
        return _FAKE_PNG_CACHE

    img = Image.new("RGB", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    _FAKE_PNG_CACHE = buf.getvalue()
    return _FAKE_PNG_CACHE


class FakeCoverPort(CoverGenerationPort):
    """Fake cover port that returns synthetic images.

    Configurable behavior:
    - succeed: Generate valid image
    - fail_quality: Generate image that fails quality check (too small)
    - fail_unavailable: Simulate provider unavailable
    """

    def __init__(
        self,
        mode: str = "succeed",
        image_size: int = 10000,
    ):
        """Initialize fake port.

        Args:
            mode: Behavior mode (succeed, fail_quality, fail_unavailable)
            image_size: Size of generated image in bytes
        """
        self.mode = mode
        self.image_size = image_size
        self.call_count = 0
        self.last_prompt = None
        self.last_spec = None
        self.last_seed = None

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.mode != "fail_unavailable"

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Generate fake cover image.

        Args:
            prompt: Text prompt
            spec: Image specifications
            seed: Random seed
            workflow_params: Optional workflow parameters (ignored in fake)

        Returns:
            Fake image bytes

        Raises:
            DomainError: If mode is fail_*
        """
        self.call_count += 1
        self.last_prompt = prompt
        self.last_spec = spec
        self.last_seed = seed

        if self.mode == "fail_unavailable":
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="Fake provider unavailable",
                actionable_hint="Check fake configuration",
            )

        if self.mode == "fail_quality":
            # Return image that's too small
            return b"FAKE_COVER_TOO_SMALL"

        # Return valid fake PNG image
        return _make_fake_png()

    async def remove_text_from_cover(
        self,
        image_bytes: bytes,
        spec: ImageSpec,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.2,
        barcode_margin_inches: float = 0.25,
    ) -> bytes:
        """Remove text from cover to create back cover using AI vision.

        Args:
            image_bytes: Original cover image (with text)
            spec: Image specifications (unused in fake, kept for interface compatibility)
            barcode_width_inches: KDP barcode width in inches (default: 2.0)
            barcode_height_inches: KDP barcode height in inches (default: 1.2)
            barcode_margin_inches: KDP barcode margin in inches (default: 0.25)

        Returns:
            Same image without text with KDP-compliant barcode space (for back cover)
        """
        # For testing, just return the same bytes or a modified version
        return image_bytes
