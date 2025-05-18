from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleAuthService:
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self._credentials: Optional[service_account.Credentials] = None

    def get_credentials(self) -> service_account.Credentials:
        """Récupère les credentials Google à partir du fichier JSON"""
        if self._credentials is None:
            self._credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=["https://www.googleapis.com/auth/drive"]
            )
        return self._credentials

    def get_drive_service(self):
        """Crée et retourne un service Google Drive"""
        credentials = self.get_credentials()
        return build("drive", "v3", credentials=credentials)
