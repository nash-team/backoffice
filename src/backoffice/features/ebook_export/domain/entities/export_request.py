"""Export request value object for ebook export feature."""

from dataclasses import dataclass
from enum import Enum


class ExportType(str, Enum):
    """Types of ebook exports available."""

    PDF = "pdf"  # Raw PDF download from database
    KDP = "kdp"  # Amazon KDP format (with bleed/trim adjustments)


@dataclass(frozen=True)
class ExportRequest:
    """Value object representing an ebook export request.

    This encapsulates all parameters needed to export an ebook,
    with validation rules enforced in __post_init__.

    Business rules:
    - ebook_id must be positive
    - export_type must be a valid ExportType
    - preview_mode only applies to KDP exports
    """

    ebook_id: int
    export_type: ExportType
    preview_mode: bool = False

    def __post_init__(self) -> None:
        """Validate business rules."""
        # Business rule: ebook_id must be positive
        if self.ebook_id <= 0:
            raise ValueError(f"ebook_id must be positive, got {self.ebook_id}")

        # Business rule: export_type must be valid
        if not isinstance(self.export_type, ExportType):
            raise ValueError(f"Invalid export_type: {self.export_type}")

        # Business rule: preview_mode only applies to KDP exports
        if self.preview_mode and self.export_type != ExportType.KDP:
            raise ValueError("preview_mode only applies to KDP exports")
