import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backoffice.features.ebook.creation.presentation.routes import (
    router as ebook_creation_router,
)
from backoffice.features.ebook.creation.presentation.routes.form_routes import (
    router as ebook_form_router,
)
from backoffice.features.ebook.export.presentation.routes import router as ebook_export_router
from backoffice.features.ebook.lifecycle.presentation.routes import (
    router as ebook_lifecycle_router,
)
from backoffice.features.ebook.listing.presentation.routes import router as ebook_listing_router
from backoffice.features.ebook.regeneration.presentation.routes import (
    router as ebook_regeneration_router,
)
from backoffice.features.shared.presentation.routes.templates import templates

# Configure logging level based on environment
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(title="Backoffice")


# Configuration CORS basée sur l'environnement
def get_cors_origins() -> list[str]:
    """Configure CORS origins based on environment."""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        # En production, spécifier les domaines autorisés
        return ["https://yourdomain.com", "https://www.yourdomain.com"]
    elif env == "staging":
        return ["https://staging.yourdomain.com", "http://localhost:3000"]
    else:
        # En développement, autoriser localhost sur différents ports
        return [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
        ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "features" / "shared" / "presentation" / "static"),
    name="static",
)


@app.get("/")
async def dashboard_page(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Test reset endpoint pour isolation de données
@app.post("/__test__/reset")
async def test_reset_database() -> tuple[dict[str, str], int] | dict[str, str]:
    """Reset complet de la base de données pour les tests."""
    import os

    if not os.getenv("TESTING"):
        return {"error": "Only available in testing mode"}, 403

    try:
        # Importer et utiliser les modèles pour reset la DB
        from backoffice.features.ebook.shared.infrastructure.models.ebook_model import EbookModel
        from backoffice.features.shared.infrastructure.database import get_db

        db = next(get_db())
        # Supprimer toutes les données
        db.query(EbookModel).delete()
        db.commit()

        return {"status": "reset_ok"}
    except Exception as e:
        return {"error": str(e)}, 500


# Register all feature routes
app.include_router(ebook_listing_router)
app.include_router(ebook_creation_router)
app.include_router(ebook_form_router)
app.include_router(ebook_lifecycle_router)
app.include_router(ebook_export_router)
app.include_router(ebook_regeneration_router)

if __name__ == "__main__":
    import uvicorn

    # Configuration host basée sur l'environnement
    env = os.getenv("ENVIRONMENT", "development")
    host = "127.0.0.1" if env == "development" else "0.0.0.0"
    port = int(os.getenv("PORT", 8001))

    uvicorn.run(app, host=host, port=port)
