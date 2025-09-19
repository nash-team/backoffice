import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backoffice.presentation.routes import init_routes

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
    "/presentation/static",
    StaticFiles(directory=BASE_DIR / "presentation" / "static"),
    name="static",
)


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
        from backoffice.infrastructure.database import get_db
        from backoffice.infrastructure.models.ebook_model import EbookModel

        db = next(get_db())
        # Supprimer toutes les données
        db.query(EbookModel).delete()
        db.commit()

        return {"status": "reset_ok"}
    except Exception as e:
        return {"error": str(e)}, 500


# Initialisation des routes
init_routes(app)

if __name__ == "__main__":
    import uvicorn

    # Configuration host basée sur l'environnement
    env = os.getenv("ENVIRONMENT", "development")
    host = "127.0.0.1" if env == "development" else "0.0.0.0"
    port = int(os.getenv("PORT", 8001))

    uvicorn.run(app, host=host, port=port)
