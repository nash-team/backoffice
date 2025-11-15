"""Strategy for generating coloring books (V1 slim)."""

import logging
from pathlib import Path

from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage
from backoffice.features.ebook.shared.domain.ports.ebook_generation_strategy_port import (
    EbookGenerationStrategyPort,
)
from backoffice.features.ebook.shared.domain.services.cover_generation import CoverGenerationService
from backoffice.features.ebook.shared.domain.services.page_generation import (
    ContentPageGenerationService,
)
from backoffice.features.ebook.shared.domain.services.pdf_assembly import PDFAssemblyService
from backoffice.features.ebook.shared.domain.services.prompt_template_engine import (
    PromptTemplateEngine,
)
from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
    ThemeRepository,
)
from backoffice.features.shared.domain.entities.generation_request import (
    ColorMode,
    GenerationRequest,
    GenerationResult,
    ImageSpec,
    PageMeta,
)

logger = logging.getLogger(__name__)


class ColoringBookStrategy(EbookGenerationStrategyPort):
    """Strategy for generating coloring books (V1 slim).

    V1 approach:
    - Log execution plan BEFORE starting
    - Generate cover (colorful) based on page themes using CoverGenerationService (Gemini)
    - Create back cover (text removal from cover)
    - Assemble PDF using PDFAssemblyService
    - Return GenerationResult with pages_meta

    Order changed: Pages FIRST → Cover SECOND (for visual consistency)
    """

    def __init__(
        self,
        cover_service: CoverGenerationService,
        pages_service: ContentPageGenerationService,
        assembly_service: PDFAssemblyService,
        theme_repository: ThemeRepository | None = None,
    ):
        """Initialize coloring book strategy.

        Args:
            cover_service: Service for cover generation
            pages_service: Service for content page generation
            assembly_service: Service for PDF assembly
            theme_repository: Repository for loading theme configurations
                (optional, creates default if None)
        """
        self.cover_service = cover_service
        self.pages_service = pages_service
        self.assembly_service = assembly_service
        self.theme_repository = theme_repository or ThemeRepository()

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
        logger.info(f"   Audience: {request.audience.value}")
        logger.info(f"   Page count: {request.page_count}")
        logger.info(f"   Seed: {request.seed}")

        # Log execution plan
        self._log_execution_plan(request)

        # Step 1: Generate cover (colorful) FIRST
        logger.info("\n📋 Step 1/4: Generating cover...")
        # Cost tracking now handled via events in provider

        cover_prompt = self._build_cover_prompt(request, page_prompts=None)
        cover_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.COLOR,
        )

        cover_data = await self.cover_service.generate_cover(
            prompt=cover_prompt,
            spec=cover_spec,
            seed=request.seed,
        )

        # Step 2: Generate content pages (B&W) SECOND
        logger.info(f"\n📋 Step 2/4: Generating {request.page_count} content pages...")

        page_prompts = self._build_page_prompts(request)
        page_spec = ImageSpec(
            width_px=2626,
            height_px=2626,
            format="PNG",
            dpi=300,
            color_mode=ColorMode.BLACK_WHITE,
        )

        pages_data = await self.pages_service.generate_pages(
            prompts=page_prompts,
            spec=page_spec,
            seed=request.seed,
        )

        # Step 3: Remove text from cover to create back cover with Gemini Vision
        logger.info("\n📋 Step 3/4: Creating back cover (same image without text)...")

        # Load KDP config for barcode dimensions
        from backoffice.features.ebook.shared.domain.entities.ebook import KDPExportConfig

        kdp_config = KDPExportConfig()

        back_cover_data = await self.cover_service.cover_port.remove_text_from_cover(
            cover_bytes=cover_data,
            barcode_width_inches=kdp_config.barcode_width,
            barcode_height_inches=kdp_config.barcode_height,
            barcode_margin_inches=kdp_config.barcode_margin,
        )

        # Step 4: Assemble PDF
        logger.info("\n📋 Step 4/4: Assembling PDF...")
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

        # Add back cover as last page
        back_cover_page = AssembledPage(
            page_number=len(pages_data) + 1,
            title="Back Cover",
            image_data=back_cover_data,
            image_format="PNG",
        )

        pdf_uri = await self.assembly_service.assemble_ebook(
            cover=cover_page,
            pages=content_pages + [back_cover_page],  # Include back cover
            output_path=output_path,
        )

        # Build result with image data for regeneration
        pages_meta = (
            [
                PageMeta(
                    page_number=0,
                    title="Cover",
                    format="PNG",
                    size_bytes=len(cover_data),
                    image_data=cover_data,
                )
            ]
            + [
                PageMeta(
                    page_number=i + 1,
                    title=f"Page {i + 1}",
                    format="PNG",
                    size_bytes=len(page_data),
                    image_data=page_data,
                )
                for i, page_data in enumerate(pages_data)
            ]
            + [
                PageMeta(
                    page_number=len(pages_data) + 1,
                    title="Back Cover",
                    format="PNG",
                    size_bytes=len(back_cover_data),
                    image_data=back_cover_data,
                )
            ]
        )

        logger.info("\n✅ Coloring book generated successfully!")
        logger.info(f"   PDF: {pdf_uri}")
        logger.info(f"   Total pages: {len(pages_meta)} (includes back cover)")

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
        logger.info(f"Audience: {request.audience.value}")
        logger.info(
            f"Total pages: {request.page_count + 1} (1 cover + {request.page_count} content)"
        )
        logger.info(f"Seed: {request.seed or 'random'}")
        logger.info("\nSteps:")
        logger.info("  1. Generate colorful cover with 'Coloring Book' text (Gemini)")
        logger.info(f"  2. Generate {request.page_count} B&W coloring pages (Gemini)")
        logger.info("  3. Create back cover (text removal from cover)")
        logger.info("  4. Assemble PDF (WeasyPrint)")
        logger.info("\nQuality settings:")
        logger.info('  - Cover: 2626x2626, 300 DPI, color (KDP 8.5×8.5" + bleed)')
        logger.info("  - Pages: 2626x2626, 300 DPI, B&W line art")
        logger.info("  - Back: Same as cover without text")
        logger.info("=" * 80 + "\n")

    def _build_cover_prompt(
        self, request: GenerationRequest, page_prompts: list[str] | None = None
    ) -> str:
        """Build prompt for cover generation WITH text using theme YAML configuration.

        Args:
            request: Generation request
            page_prompts: Optional list of page prompts to inspire cover (if pages generated first)

        Returns:
            Cover prompt based on theme configuration and brand identity
        """
        from backoffice.config import ConfigLoader

        # Load theme from YAML
        theme_profile = self.theme_repository.get_theme_by_id(request.theme)

        # Load brand identity for style guidelines
        config = ConfigLoader()
        identity = config.load_brand_identity()
        style_guide = identity["style_guidelines"]

        # Build simplified, direct prompt (less verbose = better AI compliance)
        colors_str = ", ".join(theme_profile.palette.base[:3])
        accents_str = (
            ", ".join(theme_profile.palette.accents_allowed)
            if theme_profile.palette.accents_allowed
            else "white"
        )
        forbidden_str = ", ".join(theme_profile.palette.forbidden_keywords)

        # Extract style guide values
        illustration_style = style_guide["illustration"]["style"]
        mood = style_guide["mood"]["overall"]

        base_prompt = f"""Coloring book cover. {illustration_style}, {mood}.

Scene: {theme_profile.blocks.subject}, {theme_profile.blocks.environment}

Colors to use: {colors_str}, {accents_str}
Do NOT use: {forbidden_str}, turquoise, cyan

Text: Only "{request.title}" - NO age numbers, NO "Ages 2-4" or similar"""

        # If pages were generated first, add context from page themes
        if page_prompts and len(page_prompts) > 0:
            # Extract common visual elements from first few pages (max 3 for brevity)
            sample_pages = page_prompts[: min(3, len(page_prompts))]
            context = (
                "\n\nCONTEXT: The book includes pages featuring: "
                + ", ".join(prompt.split(".")[0].lower() for prompt in sample_pages)
                + "."
            )
            return base_prompt + context

        return base_prompt

    def _build_back_cover_prompt(self, request: GenerationRequest, front_cover_bytes: bytes) -> str:
        """Build prompt for back cover generation (line art style) using theme YAML configuration.

        Args:
            request: Generation request
            front_cover_bytes: Front cover for color extraction

        Returns:
            Back cover prompt for line art generation based on theme
            configuration and brand identity
        """

        from backoffice.config import ConfigLoader
        from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.color_utils import (  # noqa: E501
            extract_dominant_color_exact,
        )

        # Load theme from YAML
        theme_profile = self.theme_repository.get_theme_by_id(request.theme)

        # Load brand identity for style guidelines
        config = ConfigLoader()
        identity = config.load_brand_identity()
        style_guide = identity["style_guidelines"]

        # Extract background color from front cover
        bg_color = extract_dominant_color_exact(front_cover_bytes)
        bg_hex = "#{:02x}{:02x}{:02x}".format(*bg_color)

        # Build prompt using theme configuration + brand identity
        theme_label = theme_profile.label
        prompt_parts = [
            f"Create a simple LINE ART illustration for a {theme_label} coloring book back cover.",
            "",
            "BRAND STYLE (line art version):",
            f"- Illustration: {style_guide['illustration']['style']} (simplified for back cover)",
            f"- Line weight: {style_guide['illustration']['line_weight']}",
            f"- Mood: {style_guide['mood']['overall']}",
            "",
            "⚠️ CRITICAL STYLE REQUIREMENTS (MUST FOLLOW EXACTLY):",
            "- BLACK LINE ART ONLY (coloring book outline style)",
            f"- Background color: {bg_hex} (solid color, EXACTLY as front cover)",
            "- Clean, thick black lines (2-3px width)",
            "- ABSOLUTELY NO interior shading",
            "- ABSOLUTELY NO gradients",
            "- ABSOLUTELY NO text or letters",
            "- ABSOLUTELY NO colors except black lines and the specified background",
            "- Simple, centered composition",
            "- Simpler than front cover (this is the back)",
            "- Full-bleed design filling the entire frame",
            "",
            "⛔ FORBIDDEN ELEMENTS:",
            "- NO rainbow colors",
            "- NO bright neon",
            "- NO text, numbers, or age labels",
            "- NO filled colors inside the line art",
            "",
            # Subject from theme (simplified for back cover)
            f"SUBJECT: Simplified version of - {theme_profile.blocks.subject}",
            "",
            # Environment from theme
            f"ENVIRONMENT: {theme_profile.blocks.environment}",
            "",
            "MUST INCLUDE (from theme):",
        ]

        # Add some positives from theme (limit to 3 for back cover simplicity)
        for positive in theme_profile.blocks.positives[:3]:
            prompt_parts.append(f"- {positive}")

        prompt_parts.extend(
            [
                "",
                "MUST AVOID (from theme):",
            ]
        )

        # Add negatives from theme
        for negative in theme_profile.blocks.negatives:
            prompt_parts.append(f"- {negative}")

        prompt_parts.extend(
            [
                "",
                "IMPORTANT - BARCODE SPACE:",
                "- MUST leave a PLAIN WHITE EMPTY RECTANGLE in the bottom-right corner",
                "- DO NOT draw any barcode, lines, or patterns in this space",
                "- Just a solid white empty box",
                "- Rectangle size: approximately 15% of image width, 8% of image height",
                "- Position: bottom-right corner with small margin from edges",
                "- Keep all illustrations AWAY from this white rectangle area",
                "",
                f"Target audience: {request.audience.value}",
            ]
        )

        return "\n".join(prompt_parts)

    def _build_page_prompts(self, request: GenerationRequest) -> list[str]:
        """Build prompts for content page generation using template engine.

        Args:
            request: Generation request

        Returns:
            List of page prompts with varied compositions
        """
        # Initialize template engine with request seed for reproducibility
        engine = PromptTemplateEngine(seed=request.seed)

        # Generate varied prompts based on theme
        prompts = engine.generate_prompts(
            theme=request.theme, count=request.page_count, audience=request.audience.value
        )

        logger.info(f"Generated {len(prompts)} varied prompts using template engine")
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
