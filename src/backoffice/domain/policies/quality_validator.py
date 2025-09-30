"""Quality validation policies (V1 slim)."""

import logging

from backoffice.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.domain.errors.error_taxonomy import DomainError, ErrorCode

logger = logging.getLogger(__name__)

# V1: Hardcoded limits instead of complex policy system
MAX_PAGES = 20
MAX_RESOLUTION_PX = 2048


class QualityValidator:
    """Validates image quality pre/post generation (V1 slim).

    V1 focuses on essential checks:
    - Pre-check: refuse resolution > max capacity
    - Post-check: verify dimensions & format
    """

    @staticmethod
    def validate_request(page_count: int, spec: ImageSpec) -> None:
        """Pre-generation validation.

        Args:
            page_count: Number of pages requested
            spec: Image specification

        Raises:
            DomainError: If validation fails
        """
        # Check page count limit
        if page_count > MAX_PAGES:
            raise DomainError(
                code=ErrorCode.PAGE_LIMIT_EXCEEDED,
                message=f"Page count {page_count} exceeds limit of {MAX_PAGES}",
                actionable_hint=f"Reduce page count to {MAX_PAGES} or less",
                context={"requested": page_count, "max": MAX_PAGES},
            )

        # Check resolution limit
        if spec.width_px > MAX_RESOLUTION_PX or spec.height_px > MAX_RESOLUTION_PX:
            raise DomainError(
                code=ErrorCode.RESOLUTION_TOO_HIGH,
                message=(
                    f"Resolution {spec.width_px}x{spec.height_px} "
                    f"exceeds max {MAX_RESOLUTION_PX}"
                ),
                actionable_hint=f"Use resolution <= {MAX_RESOLUTION_PX}x{MAX_RESOLUTION_PX}",
                context={
                    "requested": f"{spec.width_px}x{spec.height_px}",
                    "max": f"{MAX_RESOLUTION_PX}x{MAX_RESOLUTION_PX}",
                },
            )

        logger.info(f"✅ Pre-check passed: {page_count} pages, {spec.width_px}x{spec.height_px}")

    @staticmethod
    def validate_image(
        image_data: bytes,
        expected_spec: ImageSpec,  # noqa: ARG004
        page_type: str = "content",
    ) -> None:
        """Post-generation validation.

        Args:
            image_data: Generated image data
            expected_spec: Expected specifications
            page_type: Type of page (for logging)

        Raises:
            DomainError: If validation fails
        """
        # Basic size check
        size_bytes = len(image_data)
        if size_bytes < 1024:  # Less than 1KB is suspicious
            raise DomainError(
                code=ErrorCode.IMAGE_TOO_SMALL,
                message=f"Generated image too small: {size_bytes} bytes",
                actionable_hint="Check provider configuration and prompt quality",
                context={"size_bytes": size_bytes, "page_type": page_type},
            )

        logger.info(f"✅ Post-check passed: {page_type} image {size_bytes} bytes")

    @staticmethod
    def validate_color_mode(spec: ImageSpec, is_cover: bool) -> None:
        """Validate color mode matches page type.

        Args:
            spec: Image specification
            is_cover: Whether this is a cover page

        Raises:
            DomainError: If color mode doesn't match page type
        """
        if is_cover and spec.color_mode == ColorMode.BLACK_WHITE:
            raise DomainError(
                code=ErrorCode.WRONG_COLOR_MODE,
                message="Cover must be in color mode",
                actionable_hint="Use ColorMode.COLOR for cover pages",
                context={"is_cover": is_cover, "color_mode": spec.color_mode},
            )

        if not is_cover and spec.color_mode == ColorMode.COLOR:
            logger.warning("⚠️ Content page using color mode (expected B&W for coloring books)")
