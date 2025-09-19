import os

from dotenv import load_dotenv

from backoffice.infrastructure.adapters.auth.google_auth import GoogleAuthService

# Charger les variables d'environnement
load_dotenv()

# Récupérer le chemin des credentials depuis les variables d'environnement
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")

# Initialisation du service d'authentification
auth_service = GoogleAuthService(CREDENTIALS_PATH)
