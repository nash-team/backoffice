"""Token usage tracking and cost calculation service.

This service tracks token usage across multiple API calls during ebook generation
and calculates the total cost using a pricing adapter (following hexagonal architecture).
"""

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal

from backoffice.domain.ports.pricing_port import PricingPort
from backoffice.domain.value_objects.usage_metrics import UsageMetrics

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Single token usage record.

    Attributes:
        model: Model ID used
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        cost: Calculated cost in USD (Decimal for precision)
    """

    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: Decimal


@dataclass
class ImageUsage:
    """Single image usage record for vision/generation models.

    Attributes:
        model: Model ID used
        input_images: Number of images sent as input (vision models)
        output_images: Number of images generated as output
        cost: Calculated cost in USD (Decimal for precision)
    """

    model: str
    input_images: int
    output_images: int
    cost: Decimal


class TokenTracker:
    """Track token usage and calculate costs for ebook generation.

    This service uses a PricingPort to fetch pricing information and calculate
    costs for each API call. Thread-safe for concurrent usage tracking.
    """

    def __init__(self, request_id: str, pricing_adapter: PricingPort):
        """Initialize token tracker.

        Args:
            request_id: Unique ID for this generation request
            pricing_adapter: Pricing adapter implementation (e.g., OpenRouter)
        """
        self.request_id = request_id
        self.pricing_adapter = pricing_adapter
        self.usages: list[TokenUsage] = []
        self.image_usages: list[ImageUsage] = []
        self._pricing_table: dict | None = None
        self._lock = asyncio.Lock()  # Thread-safe for concurrent add_usage

    async def _ensure_pricing(self):
        """Lazy load pricing table from adapter."""
        if self._pricing_table is None:
            self._pricing_table = await self.pricing_adapter.get_pricing()

    async def add_usage(self, model: str, prompt_tokens: int, completion_tokens: int):
        """Add token usage and calculate cost.

        Args:
            model: Model ID used
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
        """
        async with self._lock:  # Thread-safe
            await self._ensure_pricing()
            cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
            self.usages.append(TokenUsage(model, prompt_tokens, completion_tokens, cost))

            logger.info(
                f"📊 Tokens - {model} | "
                f"Prompt: {prompt_tokens} | "
                f"Completion: {completion_tokens} | "
                f"Cost: ${cost}"
            )

    async def add_usage_metrics(self, metrics: UsageMetrics):
        """Add usage metrics from any provider (provider-agnostic).

        Args:
            metrics: UsageMetrics extracted by the provider
        """
        async with self._lock:
            # Create TokenUsage from UsageMetrics (same structure)
            usage = TokenUsage(
                model=metrics.model,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                cost=metrics.cost,
            )
            self.usages.append(usage)
            logger.info(
                f"📊 Usage added - {metrics.model} | "
                f"Prompt: {metrics.prompt_tokens} | "
                f"Completion: {metrics.completion_tokens} | "
                f"Cost: ${metrics.cost:.6f}"
            )

    async def add_usage_from_openrouter_response(self, response, model: str):
        """Extract usage and real cost from OpenRouter response.

        OpenRouter's Usage Accounting provides the REAL cost (including platform fees),
        which is more accurate than calculating from pricing API.

        Args:
            response: OpenRouter API response with usage data
            model: Model ID used
        """
        async with self._lock:  # Thread-safe
            if not hasattr(response, "usage") or not response.usage:
                logger.warning("⚠️ No usage data in OpenRouter response")
                return

            usage_data = response.usage
            prompt_tokens = usage_data.prompt_tokens or 0
            completion_tokens = usage_data.completion_tokens or 0

            # Try to get REAL cost from OpenRouter (includes platform fees)
            real_cost = None
            if hasattr(usage_data, "cost") and usage_data.cost is not None:
                real_cost = Decimal(str(usage_data.cost))
                logger.info(f"💰 OpenRouter real cost: ${real_cost} (includes platform fees)")

            # Fallback: calculate if OpenRouter didn't provide cost
            if real_cost is None:
                await self._ensure_pricing()
                real_cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
                logger.warning(
                    f"⚠️ Using calculated cost ${real_cost} (OpenRouter didn't provide real cost)"
                )
            else:
                # Compare real vs calculated to show platform fee overhead
                await self._ensure_pricing()
                calculated_cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
                overhead = real_cost - calculated_cost
                if overhead > Decimal("0.0001"):  # Significant difference
                    overhead_pct = (overhead / calculated_cost * 100) if calculated_cost > 0 else 0
                    logger.info(
                        f"📈 Platform overhead: ${overhead:.6f} "
                        f"({overhead_pct:.1f}% above base pricing)"
                    )

            # Store with real cost
            self.usages.append(TokenUsage(model, prompt_tokens, completion_tokens, real_cost))

            logger.info(
                f"📊 Tokens - {model} | "
                f"Prompt: {prompt_tokens} | "
                f"Completion: {completion_tokens} | "
                f"Real Cost: ${real_cost}"
            )

    async def add_image_usage(self, model: str, input_images: int = 0, output_images: int = 1):
        """Add image generation usage and calculate cost.

        Args:
            model: Model ID used
            input_images: Number of images sent as input (for vision models)
            output_images: Number of images generated as output
        """
        async with self._lock:  # Thread-safe
            await self._ensure_pricing()
            cost = self._calculate_image_cost(model, input_images, output_images)
            self.image_usages.append(ImageUsage(model, input_images, output_images, cost))

            logger.info(
                f"🖼️  Images - {model} | "
                f"Input: {input_images} | "
                f"Output: {output_images} | "
                f"Cost: ${cost}"
            )

    def get_total_cost(self) -> Decimal:
        """Get total cost in USD (Decimal for precision).

        Returns:
            Total cost across all tracked usages (tokens + images)
        """
        token_cost = sum((u.cost for u in self.usages), Decimal("0"))
        image_cost = sum((u.cost for u in self.image_usages), Decimal("0"))
        return token_cost + image_cost

    def get_total_prompt_tokens(self) -> int:
        """Get total prompt tokens across all usages.

        Returns:
            Total prompt tokens
        """
        return sum(u.prompt_tokens for u in self.usages)

    def get_total_completion_tokens(self) -> int:
        """Get total completion tokens across all usages.

        Returns:
            Total completion tokens
        """
        return sum(u.completion_tokens for u in self.usages)

    def get_total_input_images(self) -> int:
        """Get total input images across all usages.

        Returns:
            Total input images
        """
        return sum(u.input_images for u in self.image_usages)

    def get_total_output_images(self) -> int:
        """Get total output images across all usages.

        Returns:
            Total output images
        """
        return sum(u.output_images for u in self.image_usages)

    def _calculate_cost(self, model: str, prompt: int, completion: int) -> Decimal:
        """Calculate cost for a single usage.

        Args:
            model: Model ID
            prompt: Number of prompt tokens
            completion: Number of completion tokens

        Returns:
            Cost in USD (Decimal)
        """
        if not self._pricing_table:
            logger.warning("⚠️ Pricing table not loaded")
            return Decimal("0")

        pricing = self._pricing_table.get(model)

        if not pricing:
            logger.warning(f"⚠️ No pricing found for model: {model}")
            return Decimal("0")

        # ALWAYS calculate token costs if tokens are provided
        # Even image models charge for tokens (prompt/completion)
        prompt_cost = Decimal(prompt) * pricing["prompt_per_token"]
        completion_cost = Decimal(completion) * pricing["completion_per_token"]
        token_cost: Decimal = prompt_cost + completion_cost

        logger.debug(
            f"Token pricing: ${prompt_cost:.6f} + ${completion_cost:.6f} = ${token_cost:.6f}"
        )

        # Note: Image costs are tracked separately via add_image_usage()
        # The "unit" field just indicates the primary billing unit
        return token_cost

    def _calculate_image_cost(self, model: str, input_images: int, output_images: int) -> Decimal:
        """Calculate cost for image generation/processing.

        Args:
            model: Model ID
            input_images: Number of images sent as input
            output_images: Number of images generated as output

        Returns:
            Cost in USD (Decimal)
        """
        if not self._pricing_table:
            logger.warning("⚠️ Pricing table not loaded")
            return Decimal("0")

        pricing = self._pricing_table.get(model)

        if not pricing:
            logger.warning(f"⚠️ No pricing found for model: {model}")
            return Decimal("0")

        total_cost = Decimal("0")

        # Input images cost (for vision models)
        if input_images > 0 and pricing.get("input_images_per_k"):
            input_cost_per_k = pricing["input_images_per_k"]
            input_cost = (Decimal(str(input_images)) / Decimal("1000")) * input_cost_per_k
            total_cost += input_cost
            logger.debug(f"Input images: {input_images} × ${input_cost_per_k}/K = ${input_cost}")

        # Output images cost (for generation models)
        if output_images > 0 and pricing.get("output_images_per_k"):
            output_cost_per_k = pricing["output_images_per_k"]
            output_cost = (Decimal(str(output_images)) / Decimal("1000")) * output_cost_per_k
            total_cost += output_cost
            logger.debug(
                f"Output images: {output_images} × ${output_cost_per_k}/K = ${output_cost}"
            )

        # Fallback: if no per-image pricing, use per_request
        if total_cost == Decimal("0") and pricing.get("per_request"):
            total_cost = pricing["per_request"]
            logger.debug(f"Using per_request pricing: ${total_cost}")

        return total_cost
