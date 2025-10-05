"""Use case for tracking token usage during generation."""

import logging
from decimal import Decimal

from backoffice.features.generation_costs.domain.entities.token_usage import ImageUsage, TokenUsage
from backoffice.features.generation_costs.domain.events.tokens_consumed_event import (
    TokensConsumedEvent,
)
from backoffice.features.generation_costs.domain.ports.token_tracker_port import TokenTrackerPort
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class TrackTokenUsageUseCase:
    """Use case for tracking and persisting token usage.

    Receives token usage data from API calls, persists it, and emits
    a TokensConsumedEvent for other features to react to.
    """

    def __init__(self, token_tracker: TokenTrackerPort, event_bus: EventBus):
        """Initialize use case.

        Args:
            token_tracker: Port for persisting token usage
            event_bus: Event bus for publishing events
        """
        self.token_tracker = token_tracker
        self.event_bus = event_bus

    async def execute(
        self,
        request_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: Decimal,
    ) -> None:
        """Track token usage for an API call.

        Args:
            request_id: Generation request ID
            model: Model ID used
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            cost: Calculated cost in USD
        """
        logger.info(
            f"📊 Tracking token usage - {model} | "
            f"Prompt: {prompt_tokens} | "
            f"Completion: {completion_tokens} | "
            f"Cost: ${cost}"
        )

        # Create token usage entity
        usage = TokenUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
        )

        # Persist usage
        await self.token_tracker.save_token_usage(request_id, usage)

        # Emit event
        event = TokensConsumedEvent(
            request_id=request_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
        )
        await self.event_bus.publish(event)

        logger.info(f"✅ Token usage tracked for request {request_id}")

    async def execute_image_usage(
        self,
        request_id: str,
        model: str,
        input_images: int,
        output_images: int,
        cost: Decimal,
    ) -> None:
        """Track image usage for an API call.

        Args:
            request_id: Generation request ID
            model: Model ID used
            input_images: Number of input images
            output_images: Number of output images
            cost: Calculated cost in USD
        """
        logger.info(
            f"🖼️  Tracking image usage - {model} | "
            f"Input: {input_images} | "
            f"Output: {output_images} | "
            f"Cost: ${cost}"
        )

        # Create image usage entity
        usage = ImageUsage(
            model=model,
            input_images=input_images,
            output_images=output_images,
            cost=cost,
        )

        # Persist usage
        await self.token_tracker.save_image_usage(request_id, usage)

        # Note: Could emit ImageGeneratedEvent here if needed
        logger.info(f"✅ Image usage tracked for request {request_id}")
