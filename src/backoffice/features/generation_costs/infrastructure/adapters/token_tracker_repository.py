"""Repository adapter for token usage tracking."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backoffice.features.generation_costs.domain.entities.cost_calculation import CostCalculation
from backoffice.features.generation_costs.domain.entities.token_usage import ImageUsage, TokenUsage
from backoffice.features.generation_costs.domain.ports.token_tracker_port import TokenTrackerPort
from backoffice.features.generation_costs.infrastructure.models.token_usage_model import (
    ImageUsageModel,
    TokenUsageModel,
)

logger = logging.getLogger(__name__)


class TokenTrackerRepository(TokenTrackerPort):
    """Repository adapter for persisting token usage data.

    Implements TokenTrackerPort using SQLAlchemy for database persistence.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository.

        Args:
            db: Async database session
        """
        self.db = db

    async def save_token_usage(self, request_id: str, usage: TokenUsage) -> None:
        """Save a token usage record.

        Args:
            request_id: Generation request ID
            usage: Token usage data to persist
        """
        model = TokenUsageModel(
            request_id=request_id,
            model=usage.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cost=usage.cost,
        )
        self.db.add(model)
        await self.db.commit()
        logger.debug(f"💾 Saved token usage for request {request_id}")

    async def save_image_usage(self, request_id: str, usage: ImageUsage) -> None:
        """Save an image usage record.

        Args:
            request_id: Generation request ID
            usage: Image usage data to persist
        """
        model = ImageUsageModel(
            request_id=request_id,
            model=usage.model,
            input_images=usage.input_images,
            output_images=usage.output_images,
            cost=usage.cost,
        )
        self.db.add(model)
        await self.db.commit()
        logger.debug(f"💾 Saved image usage for request {request_id}")

    async def get_cost_calculation(self, request_id: str) -> CostCalculation:
        """Retrieve cost calculation for a generation request.

        Args:
            request_id: Generation request ID

        Returns:
            CostCalculation with all usage records and totals
        """
        # Fetch token usages
        token_stmt = select(TokenUsageModel).where(TokenUsageModel.request_id == request_id)
        token_result = await self.db.execute(token_stmt)
        token_models = token_result.scalars().all()

        # Fetch image usages
        image_stmt = select(ImageUsageModel).where(ImageUsageModel.request_id == request_id)
        image_result = await self.db.execute(image_stmt)
        image_models = image_result.scalars().all()

        # Convert to domain entities
        token_usages = [
            TokenUsage(
                model=m.model,
                prompt_tokens=m.prompt_tokens,
                completion_tokens=m.completion_tokens,
                cost=m.cost,
            )
            for m in token_models
        ]

        image_usages = [
            ImageUsage(
                model=m.model,
                input_images=m.input_images,
                output_images=m.output_images,
                cost=m.cost,
            )
            for m in image_models
        ]

        return CostCalculation(
            request_id=request_id, token_usages=token_usages, image_usages=image_usages
        )

    async def get_all_cost_calculations(self) -> list[CostCalculation]:
        """Retrieve all cost calculations.

        Returns:
            List of all cost calculations, sorted by creation date descending
        """
        # Get all unique request_ids
        stmt = select(TokenUsageModel.request_id).distinct()
        result = await self.db.execute(stmt)
        request_ids = result.scalars().all()

        # Get cost calculation for each request
        calculations = []
        for request_id in request_ids:
            calculation = await self.get_cost_calculation(request_id)
            calculations.append(calculation)

        # Sort by request_id descending (simple heuristic)
        calculations.sort(key=lambda c: c.request_id, reverse=True)

        return calculations
