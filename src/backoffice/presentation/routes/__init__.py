from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import RedirectResponse

from backoffice.presentation.routes.auth import router as auth_router
from backoffice.presentation.routes.dashboard import router as dashboard_router
from backoffice.presentation.routes.ebook_routes import (
    operations_router as ebook_operations_router,
    router as ebook_router,
)
from backoffice.presentation.routes.templates import templates

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
async def costs_page(request: Request) -> Any:
    """Display costs page with data."""
    from decimal import Decimal

    from backoffice.domain.usecases.get_ebook_costs import GetEbookCostsUseCase
    from backoffice.infrastructure.database import get_db
    from backoffice.infrastructure.factories.repository_factory import RepositoryFactory

    # Get database session
    db = next(get_db())
    try:
        # Create repository factory
        factory = RepositoryFactory(db)
        ebook_repo = factory.get_ebook_repository()

        # Execute use case
        get_costs_usecase = GetEbookCostsUseCase(ebook_repo)
        cost_summaries = await get_costs_usecase.execute()

        # Calculate total cost
        total_cost = sum((s.cost for s in cost_summaries), Decimal("0"))

        return templates.TemplateResponse(
            "costs.html",
            {
                "request": request,
                "cost_summaries": cost_summaries,
                "total_cost": total_cost,
            },
        )
    finally:
        db.close()


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
