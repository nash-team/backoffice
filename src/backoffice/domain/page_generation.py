"""Content page generation service with batch processing (V1 slim)."""

import asyncio
import hashlib
import logging
from typing import ClassVar

from backoffice.domain.entities.generation_request import ImageSpec
from backoffice.domain.policies.quality_validator import QualityValidator
from backoffice.domain.ports.content_page_generation_port import ContentPageGenerationPort

logger = logging.getLogger(__name__)


class ContentPageGenerationService:
    """Service for generating content pages (V1 slim).

    V1 features:
    - Port injection (not direct provider)
    - Batch processing with simple Semaphore for concurrency control
    - Quality validation (pre/post)
    - Simple in-memory cache for idempotence (optional)
    """

    # Simple in-memory cache: hash(prompt+seed) -> bytes
    _cache: ClassVar[dict[str, bytes]] = {}

    def __init__(
        self,
        page_port: ContentPageGenerationPort,
        max_concurrent: int = 3,
        enable_cache: bool = True,
    ):
        """Initialize content page generation service.

        Args:
            page_port: Port for content page generation
            max_concurrent: Maximum concurrent page generations (Semaphore)
            enable_cache: Enable in-memory cache for idempotence
        """
        self.page_port = page_port
        self.max_concurrent = max_concurrent
        self.enable_cache = enable_cache
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def generate_single_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        token_tracker=None,
    ) -> bytes:
        """Generate a single content page.

        Args:
            prompt: Text description for the page
            spec: Image specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility
            token_tracker: Optional TokenTracker for usage tracking

        Returns:
            Page image as bytes

        Raises:
            DomainError: If generation or validation fails
        """
        logger.info("🎨 Generating single content page")

        # Pre-validation
        QualityValidator.validate_color_mode(spec, is_cover=False)

        # Check provider availability
        if not self.page_port.is_available():
            logger.error("❌ Content page provider not available")
            raise RuntimeError("Content page provider is not available")

        # Generate page
        page_data = await self.page_port.generate_page(prompt, spec, seed, token_tracker)

        # Post-validation
        QualityValidator.validate_image(
            image_data=page_data,
            expected_spec=spec,
            page_type="content_page",
        )

        logger.info(f"✅ Single page generated: {len(page_data)} bytes")
        return page_data

    async def generate_pages(
        self,
        prompts: list[str],
        spec: ImageSpec,
        seed: int | None = None,
        token_tracker=None,
    ) -> list[bytes]:
        """Generate multiple content pages in batch.

        Args:
            prompts: List of text prompts (one per page)
            prompts: Text descriptions for each page
            spec: Image specifications (dimensions, format, color mode)
            seed: Random seed base for reproducibility
            token_tracker: Optional TokenTracker for usage tracking

        Returns:
            List of page images as bytes

        Raises:
            DomainError: If generation or validation fails
        """
        page_count = len(prompts)
        logger.info(
            f"🎨 Generating {page_count} content pages (max concurrent: {self.max_concurrent})"
        )

        # Pre-validation
        QualityValidator.validate_color_mode(spec, is_cover=False)
        QualityValidator.validate_request(page_count=page_count, spec=spec)

        # Check provider availability
        if not self.page_port.is_available():
            logger.error("❌ Content page provider not available")
            raise RuntimeError("Content page provider is not available")

        # Generate pages in batch with concurrency control
        tasks = [
            self._generate_single_page(
                prompt=prompt,
                spec=spec,
                seed=seed + i if seed else None,
                page_number=i + 1,
                token_tracker=token_tracker,
            )
            for i, prompt in enumerate(prompts)
        ]

        logger.info(f"⚙️ Starting batch generation of {len(tasks)} pages...")
        pages = await asyncio.gather(*tasks)

        logger.info(f"✅ Batch generation complete: {len(pages)} pages")
        return pages

    async def _generate_single_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None,
        page_number: int,
        token_tracker=None,
    ) -> bytes:
        """Generate a single content page with concurrency control.

        Args:
            prompt: Text description of the page
            spec: Image specifications
            seed: Random seed
            page_number: Page number (for logging)
            token_tracker: Optional TokenTracker for usage tracking

        Returns:
            Page image as bytes
        """
        # Check cache first (before acquiring semaphore)
        cache_key = self._compute_cache_key(prompt, seed)
        if self.enable_cache and cache_key in self._cache:
            logger.info(f"✅ Cache hit for page {page_number} - NO COST TRACKED (cache return)")
            return self._cache[cache_key]

        # Acquire semaphore for concurrency control
        async with self._semaphore:
            logger.info(f"⚙️ Generating page {page_number}...")

            # Double-check cache after acquiring semaphore
            if self.enable_cache and cache_key in self._cache:
                logger.info(
                    f"✅ Cache hit for page {page_number} (after semaphore) - "
                    f"NO COST TRACKED (cache return)"
                )
                return self._cache[cache_key]

            # Generate page
            image_data = await self.page_port.generate_page(
                prompt=prompt,
                spec=spec,
                seed=seed,
                token_tracker=token_tracker,
            )

            # Post-validation
            QualityValidator.validate_image(
                image_data=image_data,
                expected_spec=spec,
                page_type=f"page_{page_number}",
            )

            # Store in cache
            if self.enable_cache:
                self._cache[cache_key] = image_data

            logger.info(f"✅ Page {page_number} generated: {len(image_data)} bytes")
            return image_data

    @staticmethod
    def _compute_cache_key(prompt: str, seed: int | None) -> str:
        """Compute cache key from prompt and seed.

        Args:
            prompt: Text prompt
            seed: Random seed

        Returns:
            Cache key hash
        """
        content = f"{prompt}|{seed}"
        return hashlib.sha256(content.encode()).hexdigest()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the in-memory cache (useful for testing)."""
        cls._cache.clear()
        logger.info("🗑️ Cache cleared")
