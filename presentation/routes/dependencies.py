from fastapi import Depends
import os
from dotenv import load_dotenv
from infrastructure.adapters.auth.google_auth import GoogleAuthService
from infrastructure.adapters.repositories.drive_repository import GoogleDriveRepository

# Charger les variables d'environnement
load_dotenv()

# Récupérer le chemin des credentials depuis les variables d'environnement
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")

# Initialisation du service d'authentification
auth_service = GoogleAuthService(CREDENTIALS_PATH)

def get_drive_repository() -> GoogleDriveRepository:
    """Provider pour le GoogleDriveRepository"""
    return GoogleDriveRepository(auth_service) 