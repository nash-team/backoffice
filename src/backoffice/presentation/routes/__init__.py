from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import RedirectResponse, Response

from backoffice.infrastructure.factories.repository_factory import (
    AsyncRepositoryFactory,
    get_async_repository_factory,
)
from backoffice.presentation.routes.auth import router as auth_router
from backoffice.presentation.routes.dashboard import router as dashboard_router
from backoffice.presentation.routes.ebook_routes import (
    operations_router as ebook_operations_router,
    router as ebook_router,
)
from backoffice.presentation.routes.templates import templates

AsyncRepositoryFactoryDep = Annotated[AsyncRepositoryFactory, Depends(get_async_repository_factory)]

# Legacy theme_routes commented - imports legacy code
# from backoffice.presentation.routes.theme_routes import router as theme_router

# Router pour les pages web
pages_router = APIRouter(tags=["Pages"])

# Router pour les redirections
redirect_router = APIRouter(tags=["Redirects"])


@redirect_router.get("/api/ebooks", include_in_schema=False)
async def redirect_ebooks() -> RedirectResponse:
    return RedirectResponse(url="/api/dashboard/ebooks")


@pages_router.get("/")
async def dashboard_page(request: Request) -> Any:
    return templates.TemplateResponse("dashboard.html", {"request": request})


@pages_router.get("/login")
async def login_page(request: Request) -> Any:
    return templates.TemplateResponse("login.html", {"request": request})


@pages_router.get("/dashboard/costs")
async def costs_page(request: Request, factory: AsyncRepositoryFactoryDep) -> Response:
    """Display ebook generation costs page."""
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


# Fonction pour initialiser toutes les routes
def init_routes(app: FastAPI) -> None:
    app.include_router(pages_router)
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(ebook_router)
    app.include_router(ebook_operations_router)  # Ebook operations (regeneration, etc.)
    # Legacy theme_router disabled
    # app.include_router(theme_router)
    app.include_router(redirect_router)
