"""Protocol types for export use case dependencies.

This module defines Protocol types to avoid circular imports and provide
loose coupling between the export use case and infrastructure providers.
"""

from typing import Protocol

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, KDPExportConfig
from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec


class ImageProviderProtocol(Protocol):
    """Protocol for image generation providers used in export.

    This protocol defines the minimal interface needed by ExportToKDPUseCase
    without depending on concrete provider implementations.
    """

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a cover image.

        Args:
            prompt: Text prompt for image generation
            spec: Image specification (size, format, etc.)
            seed: Optional seed for reproducibility

        Returns:
            Image bytes
        """
        ...

    async def remove_text_from_cover(
        self,
        image_bytes: bytes,
        spec: ImageSpec,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.2,
        barcode_margin_inches: float = 0.25,
    ) -> bytes:
        """Remove text from cover image for back cover.

        Args:
            image_bytes: Original cover image bytes
            spec: Image specifications
            barcode_width_inches: Width of barcode space to preserve
            barcode_height_inches: Height of barcode space to preserve
            barcode_margin_inches: Margin around barcode space

        Returns:
            Back cover image bytes with text removed
        """
        ...


class KDPAssemblyProviderProtocol(Protocol):
    """Protocol for KDP assembly providers used in export.

    This protocol defines the minimal interface needed by ExportToKDPUseCase
    without depending on concrete provider implementations.
    """

    async def assemble_kdp_paperback(
        self,
        ebook: Ebook,
        back_cover_bytes: bytes,
        front_cover_bytes: bytes,
        kdp_config: KDPExportConfig,
        isbn: str | None = None,
        spine_colors: list | None = None,
    ) -> bytes:
        """Assemble a KDP paperback PDF.

        Args:
            ebook: Ebook entity with metadata
            back_cover_bytes: Back cover image bytes
            front_cover_bytes: Front cover image bytes
            kdp_config: KDP export configuration
            isbn: Optional ISBN-13 for EAN barcode rendering on back cover
            spine_colors: spine colors for background and text

        Returns:
            PDF bytes ready for KDP upload
        """
        ...
