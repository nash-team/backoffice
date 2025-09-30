from backoffice.domain.constants import PageFormat
from backoffice.domain.services.pdf_css_generator import PdfCssGenerator


class TestPdfCssGenerator:
    """Test suite for PdfCssGenerator service"""

    def setup_method(self):
        """Set up test fixtures"""
        self.generator = PdfCssGenerator()

    def test_generate_global_css_for_a4_format(self):
        """Test CSS generation for A4 format"""
        # When
        css = self.generator.generate_global_css(PageFormat.A4)

        # Then
        assert "size: A4;" in css
        assert "margin: 2cm;" in css
        assert "@page cover {" in css
        assert ".page.cover { page: cover; }" in css

    def test_generate_global_css_for_square_format(self):
        """Test CSS generation for square 8.5x8.5 format"""
        # When
        css = self.generator.generate_global_css(PageFormat.SQUARE_8_5)

        # Then
        assert "size: 8.5in 8.5in;" in css
        assert "0.75in 0.5in 0.75in 0.5in;" in css  # KDP margins
        assert ".coloring-image {" in css

    def test_generate_global_css_includes_all_page_types(self):
        """Test that CSS includes all required page types"""
        # When
        css = self.generator.generate_global_css(PageFormat.A4)

        # Then
        assert "@page {" in css
        assert "@page cover {" in css
        assert "@page full-bleed {" in css
        assert "@page content {" in css
        assert "@page minimal {" in css

    def test_generate_global_css_includes_layout_classes(self):
        """Test that CSS includes layout classes"""
        # When
        css = self.generator.generate_global_css(PageFormat.A4)

        # Then
        assert ".page.cover { page: cover; }" in css
        assert ".page.full-bleed { page: full-bleed; }" in css
        assert ".page.content { page: content; }" in css
        assert ".page.minimal { page: minimal; }" in css
        assert ".page.standard { page: auto; }" in css

    def test_generate_global_css_includes_page_breaks(self):
        """Test that CSS includes page break rules"""
        # When
        css = self.generator.generate_global_css(PageFormat.A4)

        # Then
        assert ".page-break-before { page-break-before: always; }" in css
        assert ".page-break-after { page-break-after: always; }" in css

    def test_generate_global_css_includes_typography(self):
        """Test that CSS includes typography rules"""
        # When
        css = self.generator.generate_global_css(PageFormat.A4)

        # Then
        assert "font-family:" in css
        assert "line-height:" in css
        assert "h1, h2, h3 { page-break-after: avoid; }" in css

    def test_generate_global_css_includes_image_styles(self):
        """Test that CSS includes image styles"""
        # When
        css = self.generator.generate_global_css(PageFormat.A4)

        # Then
        assert "img {" in css
        assert "max-width: 100%;" in css
        assert "height: auto;" in css
        assert ".full-page-image {" in css

    def test_generate_global_css_format_specific_styles(self):
        """Test format-specific styles are included correctly"""
        # When - A4 format
        css_a4 = self.generator.generate_global_css(PageFormat.A4)

        # When - Square format
        css_square = self.generator.generate_global_css(PageFormat.SQUARE_8_5)

        # Then - A4 has generic content area
        assert ".content-area {" in css_a4
        assert ".coloring-image {" not in css_a4

        # Then - Square has coloring-specific styles
        assert ".coloring-image {" in css_square
        assert "object-fit: contain;" in css_square

    def test_generate_global_css_returns_non_empty_string(self):
        """Test that CSS generation returns non-empty content"""
        # When
        css = self.generator.generate_global_css(PageFormat.A4)

        # Then
        assert isinstance(css, str)
        assert len(css) > 0
        assert css.strip() != ""

    def test_generate_global_css_default_format(self):
        """Test CSS generation with default format"""
        # When
        css = self.generator.generate_global_css()

        # Then
        assert "size: A4;" in css  # Default should be A4
