from dataclasses import dataclass
from enum import Enum


class ImagePageType(Enum):
    """Type of image page in the ebook"""

    COLORING_PAGE = "coloring_page"
    ILLUSTRATION = "illustration"
    COVER_IMAGE = "cover_image"
    SEPARATOR = "separator"


class ImageFormat(Enum):
    """Supported image formats"""

    SVG = "svg"
    PNG = "png"
    JPEG = "jpeg"


@dataclass
class ImagePage:
    """Represents an image page in an ebook"""

    title: str
    image_data: bytes
    image_format: ImageFormat
    page_type: ImagePageType
    description: str | None = None
    full_bleed: bool = True  # Whether image should extend to page edges
    maintain_aspect_ratio: bool = True
    background_color: str = "white"

    # Layout specifications for PDF generation
    width_mm: float = 210  # A4 width
    height_mm: float = 297  # A4 height
    margin_mm: float = 0  # No margin for full-bleed
