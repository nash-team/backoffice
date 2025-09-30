"""Error taxonomy for domain errors with actionable messages."""

from dataclasses import dataclass
from enum import Enum


class ErrorCode(Enum):
    """Error codes for domain errors."""

    # Quality errors
    DPI_TOO_LOW = "quality.dpi_too_low"
    IMAGE_TOO_SMALL = "quality.image_too_small"
    WRONG_COLOR_MODE = "quality.wrong_color_mode"

    # Provider errors
    MODEL_UNAVAILABLE = "provider.model_unavailable"
    PROVIDER_TIMEOUT = "provider.timeout"
    PROVIDER_RATE_LIMIT = "provider.rate_limit"

    # Policy errors
    PAGE_LIMIT_EXCEEDED = "policy.page_limit_exceeded"
    RESOLUTION_TOO_HIGH = "policy.resolution_too_high"


@dataclass
class DomainError(Exception):
    """Base domain error with structured information."""

    code: ErrorCode
    message: str
    actionable_hint: str
    context: dict | None = None

    def __str__(self) -> str:
        """Format error for logging."""
        ctx_str = f" | Context: {self.context}" if self.context else ""
        return f"[{self.code.value}] {self.message}\n💡 {self.actionable_hint}{ctx_str}"
