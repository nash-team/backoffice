import logging

from backoffice.domain.entities.image_page import (
    ColoringPageRequest,
    ImageFormat,
    ImagePage,
    ImagePageType,
)
from backoffice.domain.ports.image_generation_port import ImageGenerationPort
from backoffice.domain.ports.vectorization_port import VectorizationPort

logger = logging.getLogger(__name__)


class GenerateColoringPagesUseCase:
    """Use case for generating coloring pages from URLs or descriptions"""

    def __init__(
        self,
        image_generator: ImageGenerationPort,
        vectorizer: VectorizationPort,
    ):
        self.image_generator = image_generator
        self.vectorizer = vectorizer

    async def execute(
        self,
        requests: list[ColoringPageRequest],
        convert_to_svg: bool = True,
    ) -> list[ImagePage]:
        """Generate coloring pages from requests"""
        logger.info(f"Generating {len(requests)} coloring pages (SVG: {convert_to_svg})")

        image_pages = []

        for i, req in enumerate(requests):
            try:
                logger.info(f"Processing coloring page {i+1}/{len(requests)}: {req.title}")
                image_page = await self._generate_single_coloring_page(req, convert_to_svg)
                image_pages.append(image_page)
            except Exception as e:
                logger.error(f"Error generating coloring page {i+1}: {str(e)}")
                # Create a fallback error page
                fallback_page = self._create_fallback_coloring_page(req.title, str(e))
                image_pages.append(fallback_page)

        logger.info(f"Successfully generated {len(image_pages)} coloring pages")
        return image_pages

    async def _generate_single_coloring_page(
        self,
        request: ColoringPageRequest,
        convert_to_svg: bool,
    ) -> ImagePage:
        """Generate a single coloring page"""

        # Generate image data
        if request.source_url:
            # Process existing image from URL
            logger.info(f"Processing image from URL: {request.source_url}")
            image_data = await self.image_generator.generate_image_from_url(
                request.source_url, "Convert to coloring book style with clean outlines"
            )
        elif request.generate_from_ai and request.description:
            # Generate new image from description
            logger.info(f"Generating AI image from description: {request.description}")
            image_data = await self.image_generator.generate_coloring_page_from_description(
                request.description
            )
        else:
            raise ValueError(
                "Either source_url or description with generate_from_ai=True must be provided"
            )

        # Convert to SVG if requested and vectorizer is available
        if convert_to_svg and self.vectorizer.is_available():
            logger.info("Converting to SVG format")
            try:
                svg_content = await self.vectorizer.vectorize_image(image_data)
                svg_optimized = await self.vectorizer.optimize_for_coloring(svg_content)

                return ImagePage(
                    title=request.title,
                    image_data=svg_optimized.encode("utf-8"),
                    image_format=ImageFormat.SVG,
                    page_type=ImagePageType.COLORING_PAGE,
                    description=request.description,
                    full_bleed=True,
                    maintain_aspect_ratio=True,
                )
            except Exception as e:
                logger.warning(f"SVG conversion failed, falling back to PNG: {str(e)}")
                # Fall through to PNG format

        # Use PNG format (original or fallback)
        return ImagePage(
            title=request.title,
            image_data=image_data,
            image_format=ImageFormat.PNG,
            page_type=ImagePageType.COLORING_PAGE,
            description=request.description,
            full_bleed=True,
            maintain_aspect_ratio=True,
        )

    def _create_fallback_coloring_page(self, title: str, error_message: str) -> ImagePage:
        """Create a fallback coloring page when generation fails"""
        # Simple SVG with error message and basic coloring elements
        fallback_svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="100%" height="100%" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="100%" height="100%" fill="white"/>

  <g stroke="black" stroke-width="3" fill="none">
    <!-- Border -->
    <rect x="50" y="50" width="924" height="924" rx="20"/>

    <!-- Title area -->
    <rect x="100" y="100" width="824" height="100" rx="10"/>

    <!-- Error message area -->
    <rect x="100" y="250" width="824" height="200" rx="10"/>

    <!-- Simple coloring shapes -->
    <circle cx="300" cy="600" r="80"/>
    <rect x="500" y="520" width="160" height="160" rx="20"/>
    <polygon points="700,600 750,500 800,600 775,650 725,650" />
  </g>

  <!-- Text (will be styled by CSS) -->
  <text x="512" y="150" text-anchor="middle" font-family="Arial" font-size="32" fill="black">
    {title}
  </text>

  <text x="512" y="320" text-anchor="middle" font-family="Arial" font-size="18" fill="red">
    Erreur de génération
  </text>

  <text x="512" y="350" text-anchor="middle" font-family="Arial" font-size="14" fill="gray">
    Page de coloriage de substitution
  </text>

  <text x="512" y="800" text-anchor="middle" font-family="Arial" font-size="16" fill="black">
    Colorez les formes ci-dessus
  </text>
</svg>"""

        return ImagePage(
            title=title,
            image_data=fallback_svg.encode("utf-8"),
            image_format=ImageFormat.SVG,
            page_type=ImagePageType.COLORING_PAGE,
            description=f"Page de coloriage de substitution - {error_message}",
            full_bleed=True,
            maintain_aspect_ratio=True,
        )

    def parse_image_urls(self, image_urls_text: str) -> list[ColoringPageRequest]:
        """Parse image URLs from text input and create coloring page requests"""
        if not image_urls_text.strip():
            return []

        requests = []
        urls = [url.strip() for url in image_urls_text.split("\n") if url.strip()]

        for i, url in enumerate(urls, 1):
            try:
                # Basic URL validation
                if not url.startswith(("http://", "https://")):
                    logger.warning(f"Skipping invalid URL: {url}")
                    continue

                request = ColoringPageRequest(
                    source_url=url,
                    title=f"Page de coloriage {i}",
                    generate_from_ai=False,
                )
                requests.append(request)
            except Exception as e:
                logger.warning(f"Error processing URL {url}: {str(e)}")
                continue

        logger.info(f"Parsed {len(requests)} valid image URLs from {len(urls)} provided")
        return requests
