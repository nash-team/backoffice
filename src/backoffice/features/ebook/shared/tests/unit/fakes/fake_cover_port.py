"""Fake cover generation port for testing."""

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort


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

        # Return valid fake image
        return b"F" * self.image_size  # Synthetic PNG-like data

    async def remove_text_from_cover(
        self,
        image_bytes: bytes | None = None,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.2,
        barcode_margin_inches: float = 0.25,
        cover_bytes: bytes | None = None,  # backward compatibility
    ) -> bytes:
        """Remove text from cover to create back cover using AI vision.

        Args:
            image_bytes: Original cover image (with text)
            barcode_width_inches: KDP barcode width in inches (default: 2.0)
            barcode_height_inches: KDP barcode height in inches (default: 1.2)
            barcode_margin_inches: KDP barcode margin in inches (default: 0.25)

        Returns:
            Same image without text with KDP-compliant barcode space (for back cover)
        """
        # Accept both image_bytes (current port) and cover_bytes (legacy)
        source_bytes = image_bytes or cover_bytes
        if source_bytes is None:
            raise ValueError("image_bytes is required")

        # For testing, just return the same bytes or a modified version
        return source_bytes
