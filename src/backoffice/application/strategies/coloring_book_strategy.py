"""Strategy for generating coloring books (V1 slim)."""

import logging
from pathlib import Path

from backoffice.domain.cover_generation import CoverGenerationService
from backoffice.domain.entities.generation_request import (
    ColorMode,
    GenerationRequest,
    GenerationResult,
    ImageSpec,
    PageMeta,
)
from backoffice.domain.page_generation import ContentPageGenerationService
from backoffice.domain.pdf_assembly import PDFAssemblyService
from backoffice.domain.ports.assembly_port import AssembledPage

logger = logging.getLogger(__name__)


class ColoringBookStrategy:
    """Strategy for generating coloring books (V1 slim).

    V1 approach:
    - Log execution plan BEFORE starting
    - Generate cover (colorful) using CoverGenerationService
    - Generate content pages (B&W) using ContentPageGenerationService
    - Assemble PDF using PDFAssemblyService
    - Return GenerationResult with pages_meta
    """

    def __init__(
        self,
        cover_service: CoverGenerationService,
        pages_service: ContentPageGenerationService,
        assembly_service: PDFAssemblyService,
    ):
        """Initialize coloring book strategy.

        Args:
            cover_service: Service for cover generation
            pages_service: Service for content page generation
            assembly_service: Service for PDF assembly
        """
        self.cover_service = cover_service
        self.pages_service = pages_service
        self.assembly_service = assembly_service

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate a coloring book.

        Args:
            request: Generation request with parameters

        Returns:
            GenerationResult with PDF URI and page metadata

        Raises:
            DomainError: If generation fails at any step
        """
        logger.info(f"🎨 Starting coloring book generation: {request.title}")
        logger.info(f"   Request ID: {request.request_id}")
        logger.info(f"   Theme: {request.theme}")
        logger.info(f"   Age group: {request.age_group.value}")
        logger.info(f"   Page count: {request.page_count}")
        logger.info(f"   Seed: {request.seed}")

        # Log execution plan
        self._log_execution_plan(request)

        # Step 1: Generate cover (colorful)
        logger.info("\n📋 Step 1/3: Generating cover...")
        cover_prompt = self._build_cover_prompt(request)
        cover_spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.COLOR,
        )

        cover_data = await self.cover_service.generate_cover(
            prompt=cover_prompt,
            spec=cover_spec,
            seed=request.seed,
        )

        # Step 2: Generate content pages (B&W)
        logger.info(f"\n📋 Step 2/3: Generating {request.page_count} content pages...")
        page_prompts = self._build_page_prompts(request)
        page_spec = ImageSpec(
            width_px=1024,
            height_px=1024,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.BLACK_WHITE,
        )

        pages_data = await self.pages_service.generate_pages(
            prompts=page_prompts,
            spec=page_spec,
            seed=request.seed,
        )

        # Step 3: Assemble PDF
        logger.info("\n📋 Step 3/3: Assembling PDF...")
        output_path = self._generate_output_path(request)

        cover_page = AssembledPage(
            page_number=0,
            title="Cover",
            image_data=cover_data,
            image_format="PNG",
        )

        content_pages = [
            AssembledPage(
                page_number=i + 1,
                title=f"Page {i + 1}",
                image_data=page_data,
                image_format="PNG",
            )
            for i, page_data in enumerate(pages_data)
        ]

        pdf_uri = await self.assembly_service.assemble_ebook(
            cover=cover_page,
            pages=content_pages,
            output_path=output_path,
        )

        # Build result with image data for regeneration
        pages_meta = [
            PageMeta(
                page_number=0,
                title="Cover",
                format="PNG",
                size_bytes=len(cover_data),
                image_data=cover_data,
            )
        ] + [
            PageMeta(
                page_number=i + 1,
                title=f"Page {i + 1}",
                format="PNG",
                size_bytes=len(page_data),
                image_data=page_data,
            )
            for i, page_data in enumerate(pages_data)
        ]

        logger.info("\n✅ Coloring book generated successfully!")
        logger.info(f"   PDF: {pdf_uri}")
        logger.info(f"   Total pages: {len(pages_meta)}")

        return GenerationResult(
            pdf_uri=pdf_uri,
            pages_meta=pages_meta,
        )

    def _log_execution_plan(self, request: GenerationRequest) -> None:
        """Log execution plan before starting generation.

        Args:
            request: Generation request
        """
        logger.info("\n" + "=" * 80)
        logger.info("📋 EXECUTION PLAN")
        logger.info("=" * 80)
        logger.info(f"Request ID: {request.request_id}")
        logger.info(f"Title: {request.title}")
        logger.info(f"Type: {request.ebook_type.value}")
        logger.info(f"Theme: {request.theme}")
        logger.info(f"Age group: {request.age_group.value}")
        logger.info(
            f"Total pages: {request.page_count + 1} (1 cover + {request.page_count} content)"
        )
        logger.info(f"Seed: {request.seed or 'random'}")
        logger.info("\nSteps:")
        logger.info("  1. Generate colorful cover (OpenRouter/Gemini)")
        logger.info(f"  2. Generate {request.page_count} B&W coloring pages (OpenRouter/Gemini)")
        logger.info("  3. Assemble PDF (WeasyPrint)")
        logger.info("\nQuality settings:")
        logger.info("  - Cover: 1024x1024, 300 DPI, color")
        logger.info("  - Pages: 1024x1024, 300 DPI, B&W")
        logger.info("=" * 80 + "\n")

    def _build_cover_prompt(self, request: GenerationRequest) -> str:
        """Build prompt for cover generation.

        Args:
            request: Generation request

        Returns:
            Cover prompt
        """
        return (
            f"Create a vibrant, colorful cover for a children's coloring book. "
            f"Title: '{request.title}'. "
            f"Theme: {request.theme}. "
            f"Target age: {request.age_group.value}. "
            f"Style: Engaging, playful, child-friendly. "
            f"Full-bleed illustration with rich colors."
        )

    def _build_page_prompts(self, request: GenerationRequest) -> list[str]:
        """Build prompts for content page generation.

        Args:
            request: Generation request

        Returns:
            List of page prompts
        """
        prompts = []
        for _ in range(request.page_count):
            prompt = (
                f"Simple coloring page for children aged {request.age_group.value}. "
                f"Theme: {request.theme}. "
                f"Clean black outlines, white fill areas, suitable for coloring. "
                f"NO text, NO numbers, just the illustration."
            )
            prompts.append(prompt)

        return prompts

    def _generate_output_path(self, request: GenerationRequest) -> str:
        """Generate output path for PDF.

        Args:
            request: Generation request

        Returns:
            Output path string
        """
        # Use request_id as filename
        filename = f"{request.request_id}.pdf"
        import tempfile

        output_dir = Path(tempfile.gettempdir()) / "ebooks"
        output_dir.mkdir(parents=True, exist_ok=True)

        return str(output_dir / filename)
