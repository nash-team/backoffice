from fastapi import Depends
from infrastructure.services.google_auth_service import GoogleAuthService
from infrastructure.adapters.google_drive_repository import GoogleDriveRepository
from config import CREDENTIALS_PATH

# Initialisation du service d'authentification
auth_service = GoogleAuthService(CREDENTIALS_PATH)

def get_drive_repository() -> GoogleDriveRepository:
    """Provider pour le GoogleDriveRepository"""
    return GoogleDriveRepository(auth_service) 