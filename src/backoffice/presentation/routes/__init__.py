from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import RedirectResponse

from backoffice.features.ebook_creation.presentation.routes import (
    router as ebook_creation_router,
)
from backoffice.features.ebook_lifecycle.presentation.routes import (
    router as ebook_lifecycle_router,
)
from backoffice.features.ebook_regeneration.presentation.routes import (
    router as ebook_regeneration_router,
)
from backoffice.features.generation_costs.presentation.routes import (
    pages_router as costs_pages_router,
    router as generation_costs_router,
)
from backoffice.infrastructure.factories.repository_factory import (
    AsyncRepositoryFactory,
    get_async_repository_factory,
)
from backoffice.presentation.routes.auth import router as auth_router
from backoffice.presentation.routes.dashboard import router as dashboard_router
from backoffice.presentation.routes.ebook_routes import router as ebook_router
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


# Fonction pour initialiser toutes les routes
def init_routes(app: FastAPI) -> None:
    app.include_router(pages_router)
    app.include_router(auth_router)
    # Feature routes (registered BEFORE dashboard to take precedence)
    app.include_router(ebook_creation_router)  # Creation
    app.include_router(ebook_lifecycle_router)  # Lifecycle (approve/reject)
    app.include_router(ebook_regeneration_router)  # Regeneration
    app.include_router(generation_costs_router)  # API routes
    app.include_router(costs_pages_router)  # Page routes
    # Legacy routes
    app.include_router(dashboard_router)
    app.include_router(ebook_router)
    # Legacy theme_router disabled
    # app.include_router(theme_router)
    app.include_router(redirect_router)
