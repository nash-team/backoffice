"""Fake content page generation port for testing."""

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)


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
    ) -> bytes:
        """Generate fake page image.

        Args:
            prompt: Text prompt
            spec: Image specifications
            seed: Random seed

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

        # Return valid fake image (different per call for uniqueness)
        return b"P" * self.image_size + str(self.call_count).encode()
