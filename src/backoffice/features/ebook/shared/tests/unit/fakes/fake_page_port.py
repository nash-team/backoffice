"""Fake content page generation port for testing."""

import io

from PIL import Image

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)


def _make_fake_page_png(call_count: int, width: int = 500, height: int = 500) -> bytes:
    """Create a valid PNG image for testing (> 1KB to pass quality validation).

    Uses a gradient pattern offset by call_count for uniqueness.
    """
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    offset = call_count * 37
    for y in range(height):
        for x in range(width):
            pixels[x, y] = ((x + offset) % 256, y % 256, (x + y) % 256)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class FakePagePort(ContentPageGenerationPort):
    """Fake page port that returns synthetic images.

    Configurable behavior:
    - succeed: Generate valid images
    - fail_quality: Generate images that fail quality check (too small)
    - fail_unavailable: Simulate provider unavailable
    """

    def __init__(
        self,
        mode: str = "succeed",
        image_size: int = 8000,
    ):
        """Initialize fake port.

        Args:
            mode: Behavior mode (succeed, fail_quality, fail_unavailable)
            image_size: Size of generated images in bytes
        """
        self.mode = mode
        self.image_size = image_size
        self.call_count = 0
        self.calls = []  # Track all calls

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.mode != "fail_unavailable"

    def supports_vectorization(self) -> bool:
        """Check if provider supports vectorization."""
        return False

    async def generate_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Generate fake page image.

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
        self.calls.append(
            {
                "prompt": prompt,
                "spec": spec,
                "seed": seed,
            }
        )

        if self.mode == "fail_unavailable":
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="Fake provider unavailable",
                actionable_hint="Check fake configuration",
            )

        if self.mode == "fail_quality":
            # Return image that's too small
            return b"FAKE_PAGE_TOO_SMALL"

        # Return valid PNG image (different per call for uniqueness)
        return _make_fake_page_png(self.call_count)
