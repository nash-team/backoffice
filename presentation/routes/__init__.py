from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .drive_routes import router as drive_router

# Router pour les pages web
pages_router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="presentation/templates")

# Router pour les redirections
redirect_router = APIRouter(tags=["Redirects"])

@redirect_router.get("/api/ebooks", include_in_schema=False)
async def redirect_ebooks():
    return RedirectResponse(url="/api/dashboard/ebooks")

@pages_router.get("/")
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@pages_router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Fonction pour initialiser toutes les routes
def init_routes(app):
    app.include_router(pages_router)
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(drive_router)
    app.include_router(redirect_router)