from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from infrastructure.api.routes import auth_router
from infrastructure.adapters.fastapi_dashboard import router as dashboard_router
from infrastructure.api.routes.drive_routes import router as drive_router

app = FastAPI(title="Backoffice")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des fichiers statiques et templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Inclusion des routes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(drive_router, prefix="/api", tags=["Drive"])

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
