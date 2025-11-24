"""Fake implementation of ImageEditPort for testing (Chicago-style testing)."""

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.image_edit_port import ImageEditPort


class FakeImageEditPort(ImageEditPort):
    """Fake image edit provider for testing.

    Supports controllable behavior via mode parameter.
    Tracks calls for assertion in tests (Chicago-style).

    Modes:
    - "succeed": Returns modified image (adds prefix to simulate edit)
    - "fail": Raises DomainError (simulates edit failure)
    """

    def __init__(
        self,
        mode: str = "succeed",
        edited_image_size: int = 5000,
    ):
        """Initialize fake image edit port.

        Args:
            mode: Behavior mode ("succeed" or "fail")
            edited_image_size: Size of edited image in bytes (for "succeed" mode)
        """
        self.mode = mode
        self.edited_image_size = edited_image_size

        # Track calls for assertions
        self.call_count = 0
        self.last_image: bytes | None = None
        self.last_edit_prompt: str | None = None
        self.last_spec: ImageSpec | None = None

    async def edit_image(
        self,
        image: bytes,
        edit_prompt: str,
        spec: ImageSpec,
    ) -> bytes:
        """Edit image (fake implementation).

        Args:
            image: Original image data
            edit_prompt: Text instructions for editing
            spec: Image specifications

        Returns:
            Fake edited image (modified bytes)

        Raises:
            DomainError: If mode is "fail"
        """
        # Track call
        self.call_count += 1
        self.last_image = image
        self.last_edit_prompt = edit_prompt
        self.last_spec = spec

        if self.mode == "fail":
            raise DomainError(
                code=ErrorCode.GENERATION_FAILED,
                message=f"Fake edit failed: {edit_prompt}",
                actionable_hint="This is a fake error for testing",
                context={"mode": self.mode, "edit_prompt": edit_prompt},
            )

        # Succeed mode: return modified image
        # Simulate edit by adding prefix to original image
        edited_prefix = f"EDITED[{edit_prompt[:20]}]".encode()
        fake_edited_image = edited_prefix + image

        # Adjust size if needed
        if len(fake_edited_image) < self.edited_image_size:
            padding = b"\x00" * (self.edited_image_size - len(fake_edited_image))
            fake_edited_image += padding
        else:
            fake_edited_image = fake_edited_image[: self.edited_image_size]

        return fake_edited_image

    def is_available(self) -> bool:
        """Check if provider is available (always True for fake)."""
        return True
