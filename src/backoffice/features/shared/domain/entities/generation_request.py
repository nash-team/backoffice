"""DTOs for ebook generation requests (V1 slim)."""

from dataclasses import dataclass
from enum import Enum


class EbookType(str, Enum):
    """Type of ebook to generate.

    Currently only coloring books are supported.
    """

    COLORING = "coloring"


class Audience(str, Enum):
    """Target audience for coloring books.

    Maps to config/branding/audiences.yaml:
    - CHILDREN: Simple, clear designs for kids
    - ADULTS: Detailed, intricate designs for adults
    """

    CHILDREN = "children"
    ADULTS = "adults"


class ColorMode(str, Enum):
    """Color mode for images."""

    BLACK_WHITE = "bw"
    COLOR = "color"


@dataclass(frozen=True)
class GenerationRequest:
    """Request to generate an ebook (V1 slim).

    Attributes:
        title: Ebook title
        theme: Theme description
        audience: Target audience (children/adults)
        ebook_type: Type of ebook
        page_count: Number of pages to generate
        seed: Random seed for reproducibility (optional)
        request_id: Unique identifier for this request
    """

    title: str
    theme: str
    audience: Audience
    ebook_type: EbookType
    page_count: int
    request_id: str
    seed: int | None = None


@dataclass(frozen=True)
class ImageSpec:
    """Specification for image generation (V1 slim).

    Attributes:
        width_px: Image width in pixels
        height_px: Image height in pixels
        format: Image format (PNG, SVG, etc.)
        dpi: DPI for quality (optional)
        color_mode: Color mode (optional)
    """

    width_px: int
    height_px: int
    format: str
    dpi: int | None = None
    color_mode: ColorMode | None = None


@dataclass
class PageMeta:
    """Metadata for a generated page."""

    page_number: int
    title: str
    format: str
    size_bytes: int
    image_data: bytes  # Raw image data for regeneration


@dataclass
class GenerationResult:
    """Result of ebook generation (V1 slim).

    Attributes:
        pdf_uri: URI to the generated PDF
        pages_meta: Metadata for each generated page
    """

    pdf_uri: str
    pages_meta: list[PageMeta]
