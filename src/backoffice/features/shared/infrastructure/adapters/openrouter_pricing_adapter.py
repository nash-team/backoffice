"""OpenRouter implementation of pricing port.

This adapter fetches model pricing from OpenRouter API with:
- Async lock for thread-safe caching
- Configurable TTL (default 24h)
- HTTP retry logic with exponential backoff
- Tolerance for missing pricing data
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backoffice.features.shared.domain.ports.pricing_port import ModelPricing, PricingPort

logger = logging.getLogger(__name__)


class OpenRouterPricingAdapter(PricingPort):
    """OpenRouter implementation of pricing port."""

    _cache: dict[str, ModelPricing] | None = None
    _cache_timestamp: datetime | None = None
    _cache_lock = asyncio.Lock()  # Class-level lock for thread-safety

    def __init__(self):
        """Initialize adapter with configurable cache TTL."""
        cache_hours = int(os.getenv("PRICING_CACHE_HOURS", "24"))
        self._cache_duration = timedelta(hours=cache_hours)

    async def get_pricing(self) -> dict[str, ModelPricing]:
        """Get pricing with cache (thread-safe).

        Returns:
            Dict mapping model_id -> pricing info
        """
        async with self._cache_lock:  # Protection against concurrent fetches
            now = datetime.now()

            if self._cache is None or (
                self._cache_timestamp and now - self._cache_timestamp > self._cache_duration
            ):
                self._cache = await self._load_from_api()
                self._cache_timestamp = now
                logger.info(f"✅ OpenRouter pricing cache refreshed ({len(self._cache)} models)")

            return self._cache

    def clear_cache(self) -> None:
        """Clear cache (force reload on next get_pricing())."""
        self._cache = None
        self._cache_timestamp = None
        logger.info("🔄 Pricing cache cleared")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _load_from_api(self) -> dict[str, ModelPricing]:
        """Load pricing from OpenRouter API with retry logic.

        Returns:
            Pricing table

        Raises:
            httpx.HTTPStatusError: If API call fails after retries
        """
        headers = {}
        api_key = os.getenv("LLM_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("⚠️ Rate limit hit on OpenRouter API, using cached pricing")
                return self._cache or {}
            logger.error(f"❌ HTTP error fetching OpenRouter pricing: {e}")
            raise

        table: dict[str, ModelPricing] = {}
        for m in r.json().get("data", []):
            p = m.get("pricing") or {}

            # Parse pricing with defaults for missing values
            prompt_price = Decimal(p.get("prompt", "0"))
            completion_price = Decimal(p.get("completion", "0"))

            # Parse image pricing (for vision and generation models)
            # OpenRouter uses "image" key for per-image pricing (output images)
            # Input images are billed via prompt tokens, not separately
            input_images_per_k = None
            output_images_per_k = None

            # OpenRouter returns price per image in "image" field
            # This is already per-image, but we multiply by 1000 to get per-K for consistency
            if "image" in p and p["image"] and p["image"] != "0":
                # Convert per-image price to per-1000 for our API
                per_image_price = Decimal(str(p["image"]))
                output_images_per_k = per_image_price * Decimal("1000")

            # Tolerance for missing pricing
            if (
                prompt_price == 0
                and completion_price == 0
                and not input_images_per_k
                and not output_images_per_k
            ):
                logger.debug(f"⚠️ No pricing available for model {m['id']}, using 0")

            table[m["id"]] = {
                "prompt_per_token": prompt_price,
                "completion_per_token": completion_price,
                "per_request": Decimal(p.get("request", "0")),
                "unit": "per_image"
                if (input_images_per_k or output_images_per_k or p.get("request"))
                else "per_token",
                "resolution_pricing": None,  # TODO: parse if OpenRouter provides
                "input_images_per_k": input_images_per_k,
                "output_images_per_k": output_images_per_k,
            }

        logger.info(f"✅ Loaded {len(table)} models from OpenRouter API")
        return table
