"""Cover generation service with quality validation (V1 slim)."""

import hashlib
import logging
import random
from typing import ClassVar

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec
from backoffice.features.ebook.shared.domain.policies.quality_validator import QualityValidator
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort

logger = logging.getLogger(__name__)


class CoverGenerationService:
    """Service for generating ebook covers (V1 slim).

    V1 features:
    - Port injection (not direct provider)
    - Quality validation (pre/post)
    - Simple in-memory cache for idempotence (optional)
    """

    # Simple in-memory cache: hash(prompt+seed) -> bytes
    _cache: ClassVar[dict[str, bytes]] = {}

    def __init__(
        self,
        cover_port: CoverGenerationPort,
        enable_cache: bool = True,
    ):
        """Initialize cover generation service.

        Args:
            cover_port: Port for cover image generation
            enable_cache: Enable in-memory cache for idempotence
        """
        self.cover_port = cover_port
        self.enable_cache = enable_cache

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a cover image with quality validation.

        Args:
            prompt: Text description of the cover
            spec: Image specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility (auto-generated if None)

        Returns:
            Cover image as bytes

        Raises:
            DomainError: If generation or validation fails
        """
        logger.info(f"🎨 Generating cover: {spec.width_px}x{spec.height_px} {spec.format}")

        # Auto-generate seed if not provided (ensures unique images each time)
        if seed is None:
            seed = random.randint(1, 2**31 - 1)  # noqa: S311 - Not crypto, just image generation
            logger.info(f"🎲 Auto-generated random seed: {seed}")

        # Pre-validation
        QualityValidator.validate_color_mode(spec, is_cover=True)
        QualityValidator.validate_request(page_count=1, spec=spec)

        # Check cache (idempotence)
        cache_key = self._compute_cache_key(prompt, seed)
        if self.enable_cache and cache_key in self._cache:
            logger.info("✅ Cache hit for cover - NO COST TRACKED (cache return)")
            return self._cache[cache_key]

        # Check provider availability
        if not self.cover_port.is_available():
            logger.error("❌ Cover provider not available")
            raise RuntimeError("Cover provider is not available")

        # Generate cover
        logger.info(f"Calling cover provider with seed={seed}, prompt: {prompt[:100]}...")
        image_data = await self.cover_port.generate_cover(
            prompt=prompt,
            spec=spec,
            seed=seed,
        )

        # Post-validation
        QualityValidator.validate_image(
            image_data=image_data,
            page_type="cover",
        )

        # Store in cache
        if self.enable_cache:
            self._cache[cache_key] = image_data
            logger.info(f"💾 Cached cover (cache size: {len(self._cache)})")

        logger.info(f"✅ Cover generated: {len(image_data)} bytes")
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
