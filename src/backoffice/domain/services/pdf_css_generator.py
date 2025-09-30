"""
PDF CSS Generation Service

This module is responsible for generating CSS styles for PDF rendering
based on page format specifications. Extracted from PdfRenderer for better modularity.
"""

import logging

from backoffice.domain.constants import (
    PAGE_SPECIFICATIONS,
    PageDimensions,
    PageFormat,
    PageMargins,
)

logger = logging.getLogger(__name__)


class PdfCssGenerator:
    """Service for generating CSS styles for PDF rendering based on page format."""

    def generate_global_css(self, page_format: PageFormat = PageFormat.A4) -> str:
        """
        Generate global CSS styles for PDF rendering based on page format

        Args:
            page_format: Page format to generate CSS for

        Returns:
            str: Complete CSS content for the specified page format
        """
        logger.debug(f"Generating CSS for page format: {page_format.value}")

        spec = PAGE_SPECIFICATIONS[page_format]
        dimensions: PageDimensions = spec["dimensions"]
        margins: PageMargins = spec["margins"]

        # Convert dimensions to CSS format
        page_config = self._get_page_configuration(page_format, dimensions, margins)

        css_content = f"""
        /* Global CSS for {page_format.value} format */
        {self._generate_page_rules(page_config)}

        {self._generate_body_styles()}

        {self._generate_layout_classes()}

        {self._generate_page_break_rules()}

        {self._generate_typography_styles()}

        {self._generate_image_styles()}

        {self._generate_format_specific_styles(page_format)}
        """

        logger.debug(f"Generated CSS: {len(css_content)} characters")
        return css_content

    def _get_page_configuration(
        self, page_format: PageFormat, dimensions: PageDimensions, margins: PageMargins
    ) -> dict[str, str]:
        """Get page configuration strings for CSS generation."""
        if page_format == PageFormat.SQUARE_8_5:
            return {
                "page_size": f"{dimensions.width}in {dimensions.height}in",
                "page_margins": (
                    f"{margins.inner}in {margins.outer}in {margins.inner}in {margins.outer}in"
                ),
                "cover_margins": "0",
            }
        else:  # A4 or other formats
            return {
                "page_size": "A4",
                "page_margins": "2cm",
                "cover_margins": "0",
            }

    def _generate_page_rules(self, config: dict[str, str]) -> str:
        """Generate @page rules for different page types."""
        return f"""
        @page {{
            size: {config['page_size']};
            margin: {config['page_margins']};
        }}

        /* Cover pages - full bleed */
        @page cover {{
            size: {config['page_size']};
            margin: {config['cover_margins']};
        }}

        /* Full page bleed (coloring content) */
        @page full-bleed {{
            size: {config['page_size']};
            margin: {config['cover_margins']};
        }}

        /* Standard content pages with KDP margins */
        @page content {{
            size: {config['page_size']};
            margin: {config['page_margins']};
        }}

        /* Minimal margins for special pages */
        @page minimal {{
            size: {config['page_size']};
            margin: 1cm;
        }}"""

    def _generate_body_styles(self) -> str:
        """Generate body and base element styles."""
        return """
        body {
            font-family: "Georgia", "Times New Roman", serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }"""

    def _generate_layout_classes(self) -> str:
        """Generate CSS classes for page layouts."""
        return """
        /* Apply CSS layouts */
        .page.cover { page: cover; }
        .page.full-bleed { page: full-bleed; }
        .page.content { page: content; }
        .page.minimal { page: minimal; }
        .page.standard { page: auto; }"""

    def _generate_page_break_rules(self) -> str:
        """Generate page break control rules."""
        return """
        /* Page breaks */
        .page-break-before { page-break-before: always; }
        .page-break-after { page-break-after: always; }"""

    def _generate_typography_styles(self) -> str:
        """Generate typography and text-related styles."""
        return """
        /* Typography */
        h1, h2, h3 { page-break-after: avoid; }"""

    def _generate_image_styles(self) -> str:
        """Generate image-related styles."""
        return """
        /* Image styles for different formats */
        img {
            max-width: 100%;
            height: auto;
        }

        /* Full page image style (updated for WeasyPrint compatibility) */
        .full-page-image {
            width: 100%;
            height: 100%;
            object-fit: contain;
            page-break-before: always;
        }"""

    def _generate_format_specific_styles(self, page_format: PageFormat) -> str:
        """Generate format-specific styles based on page format."""
        if page_format == PageFormat.SQUARE_8_5:
            return """
        /* Square format specific styles */
        .coloring-image {
            width: 100%;
            height: auto;
            object-fit: contain;
            display: block;
            margin: 0 auto;
        }

        /* Content area for square format - respects KDP margins */
        .content-area {
            width: 100%;
            height: 100%;
            box-sizing: border-box;
        }"""
        else:
            return """
        /* A4 format specific styles */
        .content-area {
            width: 100%;
            box-sizing: border-box;
        }"""
