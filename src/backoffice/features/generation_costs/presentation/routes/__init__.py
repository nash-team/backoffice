"""Routes for generation_costs feature.

This module provides HTTP endpoints for tracking and viewing generation costs.
All routes follow FastAPI conventions and use HTMX for dynamic UI updates.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from backoffice.features.shared.infrastructure.factories.repository_factory import (
    AsyncRepositoryFactory,
    get_async_repository_factory,
)
from backoffice.features.shared.presentation.routes.templates import templates

AsyncRepositoryFactoryDep = Annotated[AsyncRepositoryFactory, Depends(get_async_repository_factory)]

router = APIRouter(prefix="/api/generation-costs", tags=["Generation Costs"])


@router.get("/")
async def list_generation_costs(factory: AsyncRepositoryFactoryDep) -> dict:
    """List all generation costs with summary statistics.

    Returns:
        Dictionary with cost_calculations list and summary statistics
    """
    from decimal import Decimal

    from backoffice.features.generation_costs.infrastructure.adapters.token_tracker_repository import (  # noqa: E501
        TokenTrackerRepository,
    )

    token_tracker = TokenTrackerRepository(factory.db)
    cost_calculations = await token_tracker.get_all_cost_calculations()

    # Calculate summary statistics
    total_cost = sum((calc.total_cost for calc in cost_calculations), Decimal("0"))
    total_tokens = sum(calc.total_tokens for calc in cost_calculations)
    total_api_calls = sum(calc.api_call_count for calc in cost_calculations)

    # Format data for response
    cost_summaries = [
        {
            "request_id": calc.request_id,
            "total_cost": float(calc.total_cost),
            "total_tokens": calc.total_tokens,
            "total_prompt_tokens": calc.total_prompt_tokens,
            "total_completion_tokens": calc.total_completion_tokens,
            "total_input_images": calc.total_input_images,
            "total_output_images": calc.total_output_images,
            "api_call_count": calc.api_call_count,
            "average_cost_per_call": float(calc.average_cost_per_call),
        }
        for calc in cost_calculations
    ]

    return {
        "cost_summaries": cost_summaries,
        "summary_statistics": {
            "total_cost": float(total_cost),
            "total_requests": len(cost_calculations),
            "total_tokens": total_tokens,
            "total_api_calls": total_api_calls,
            "average_cost_per_request": float(total_cost / len(cost_calculations))
            if cost_calculations
            else 0.0,
        },
    }


@router.get("/{request_id}")
async def get_generation_cost_detail(request_id: str, factory: AsyncRepositoryFactoryDep) -> dict:
    """Get detailed cost breakdown for a specific generation request.

    Args:
        request_id: Generation request ID

    Returns:
        Dictionary with detailed cost calculation and breakdown
    """
    from backoffice.features.generation_costs.infrastructure.adapters.token_tracker_repository import (  # noqa: E501
        TokenTrackerRepository,
    )

    token_tracker = TokenTrackerRepository(factory.db)
    cost_calculation = await token_tracker.get_cost_calculation(request_id)

    # Format detailed breakdown
    return {
        "request_id": cost_calculation.request_id,
        "total_cost": float(cost_calculation.total_cost),
        "total_tokens": cost_calculation.total_tokens,
        "total_prompt_tokens": cost_calculation.total_prompt_tokens,
        "total_completion_tokens": cost_calculation.total_completion_tokens,
        "total_input_images": cost_calculation.total_input_images,
        "total_output_images": cost_calculation.total_output_images,
        "api_call_count": cost_calculation.api_call_count,
        "average_cost_per_call": float(cost_calculation.average_cost_per_call),
        "token_usages": [
            {
                "model": usage.model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cost": float(usage.cost),
            }
            for usage in cost_calculation.token_usages
        ],
        "image_usages": [
            {
                "model": usage.model,
                "input_images": usage.input_images,
                "output_images": usage.output_images,
                "cost": float(usage.cost),
            }
            for usage in cost_calculation.image_usages
        ],
    }


# Page routes (HTML templates)
pages_router = APIRouter(prefix="/dashboard/costs", tags=["Pages - Costs"])


@pages_router.get("")
async def costs_page(request: Request, factory: AsyncRepositoryFactoryDep) -> Response:
    """Display ebook generation costs page.

    This is the main page for viewing all generation costs with summary cards.
    """
    from decimal import Decimal

    from backoffice.features.generation_costs.infrastructure.adapters.token_tracker_repository import (  # noqa: E501
        TokenTrackerRepository,
    )

    try:
        # Get cost calculations directly from repository
        token_tracker = TokenTrackerRepository(factory.db)
        cost_calculations = await token_tracker.get_all_cost_calculations()

        # Calculate total cost
        total_cost = sum((calc.total_cost for calc in cost_calculations), Decimal("0"))

        # Format data for template
        cost_summaries = [
            {
                "request_id": calc.request_id,
                "total_cost": calc.total_cost,
                "total_tokens": calc.total_tokens,
                "api_call_count": calc.api_call_count,
                "average_cost_per_call": calc.average_cost_per_call,
            }
            for calc in cost_calculations
        ]

        return templates.TemplateResponse(
            "costs.html",
            {
                "request": request,
                "cost_summaries": cost_summaries,
                "total_cost": total_cost,
            },
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error loading costs page: {str(e)}", exc_info=True)
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Error loading costs page") from e
