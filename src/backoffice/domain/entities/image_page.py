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

    def get_svg_content(self) -> str:
        """Get SVG content as string (only for SVG format)"""
        if self.image_format != ImageFormat.SVG:
            raise ValueError("Image is not in SVG format")
        return self.image_data.decode("utf-8")

    def is_vector(self) -> bool:
        """Check if image is in vector format"""
        return self.image_format == ImageFormat.SVG

    def get_css_size(self) -> str:
        """Get CSS size specification for PDF rendering"""
        if self.full_bleed:
            return "width: 100%; height: 100%; object-fit: cover;"
        else:
            aspect = "contain" if self.maintain_aspect_ratio else "fill"
            return f"width: 100%; height: 100%; object-fit: {aspect};"


@dataclass
class ColoringPageRequest:
    """Request for generating a coloring page"""

    source_url: str | None = None
    description: str | None = None
    title: str = "Page de coloriage"
    generate_from_ai: bool = False  # Use AI to generate image from description

    def __post_init__(self):
        if not self.source_url and not self.description:
            raise ValueError("Either source_url or description must be provided")

        if not self.source_url and not self.generate_from_ai:
            raise ValueError("description requires generate_from_ai to be True")
