from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from presentation.routes import init_routes

app = FastAPI(title="Backoffice")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des fichiers statiques
app.mount("/presentation/static", StaticFiles(directory="presentation/static"), name="static")

# Initialisation des routes
init_routes(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
