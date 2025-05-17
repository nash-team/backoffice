from typing import List, Optional, Dict
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from domain.entities.ebook import Ebook, EbookStatus
from domain.ports.drive_repository import DriveRepository
from infrastructure.adapters.auth.google_auth import GoogleAuthService

class GoogleDriveError(Exception):
    """Exception personnalisée pour les erreurs Google Drive"""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

class GoogleDriveRepository(DriveRepository):
    def __init__(self, auth_service: GoogleAuthService):
        self.service = auth_service.get_drive_service()
        self.folder_id = "1okwSaBe0_P9Hkfw3MWf9P4dUKtSKX2zN"  # Votre ID de dossier
        self._cache: Dict[str, tuple[datetime, List[Ebook]]] = {}
        self._cache_duration = timedelta(minutes=5)

    def _get_cached_ebooks(self) -> Optional[List[Ebook]]:
        """Récupère les ebooks du cache s'ils sont encore valides"""
        if 'ebooks' in self._cache:
            timestamp, ebooks = self._cache['ebooks']
            if datetime.now() - timestamp < self._cache_duration:
                return ebooks
        return None

    def _update_cache(self, ebooks: List[Ebook]) -> None:
        """Met à jour le cache avec les nouveaux ebooks"""
        self._cache['ebooks'] = (datetime.now(), ebooks)

    def _handle_http_error(self, error: HttpError) -> None:
        """Gère les erreurs HTTP de l'API Google Drive"""
        status_code = error.resp.status if hasattr(error, 'resp') else None
        error_details = error.error_details if hasattr(error, 'error_details') else None
        
        if status_code == 401:
            raise GoogleDriveError(
                "Erreur d'authentification avec Google Drive. Vérifiez vos credentials.",
                status_code=status_code,
                details=error_details
            )
        elif status_code == 403:
            raise GoogleDriveError(
                "Accès refusé au dossier Google Drive. Vérifiez les permissions du compte de service.",
                status_code=status_code,
                details=error_details
            )
        elif status_code == 404:
            raise GoogleDriveError(
                "Ressource non trouvée dans Google Drive.",
                status_code=status_code,
                details=error_details
            )
        else:
            raise GoogleDriveError(
                f"Erreur Google Drive: {str(error)}",
                status_code=status_code,
                details=error_details
            )

    async def list_ebooks(self) -> List[Ebook]:
        """Récupère la liste des ebooks depuis le Drive ou le cache"""
        try:
            # Vérifier le cache d'abord
            cached_ebooks = self._get_cached_ebooks()
            if cached_ebooks is not None:
                return cached_ebooks

            # Si pas en cache, faire la requête API
            results = self.service.files().list(
                q=f"'{self.folder_id}' in parents and mimeType='application/pdf'",
                fields="files(id, name, createdTime, properties, webViewLink)"
            ).execute()
            
            ebooks = []
            for file in results.get('files', []):
                properties = file.get('properties', {})
                status = properties.get('status', 'pending')
                
                ebook = Ebook(
                    id=file['id'],
                    title=file['name'],
                    author=properties.get('author', 'Inconnu'),
                    created_at=file['createdTime'],
                    status=EbookStatus.PENDING if status == 'pending' else EbookStatus.VALIDATED,
                    preview_url=file.get('webViewLink')
                )
                ebooks.append(ebook)
            
            # Mettre en cache les résultats
            self._update_cache(ebooks)
            return ebooks
        except HttpError as error:
            self._handle_http_error(error)
        except Exception as e:
            raise GoogleDriveError(f"Erreur inattendue lors de la récupération des ebooks: {str(e)}")

    async def get_ebook(self, file_id: str) -> Optional[Ebook]:
        """Récupère un ebook spécifique depuis le Drive"""
        try:
            # Vérifier d'abord dans le cache
            cached_ebooks = self._get_cached_ebooks()
            if cached_ebooks:
                for ebook in cached_ebooks:
                    if ebook.id == file_id:
                        return ebook

            # Si pas en cache, faire la requête API
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, createdTime, properties, webViewLink"
            ).execute()
            
            properties = file.get('properties', {})
            status = properties.get('status', 'pending')
            
            return Ebook(
                id=file['id'],
                title=file['name'],
                author=properties.get('author', 'Inconnu'),
                created_at=file['createdTime'],
                status=EbookStatus.PENDING if status == 'pending' else EbookStatus.VALIDATED,
                preview_url=file.get('webViewLink')
            )
        except HttpError as error:
            if error.resp.status == 404:
                return None
            self._handle_http_error(error)
        except Exception as e:
            raise GoogleDriveError(f"Erreur inattendue lors de la récupération de l'ebook: {str(e)}")

    async def update_ebook_status(self, file_id: str, status: str) -> None:
        """Met à jour le statut d'un ebook dans le Drive"""
        try:
            self.service.files().update(
                fileId=file_id,
                body={'properties': {'status': status}}
            ).execute()
            
            # Invalider le cache
            self._cache.clear()
        except HttpError as error:
            self._handle_http_error(error)
        except Exception as e:
            raise GoogleDriveError(f"Erreur inattendue lors de la mise à jour du statut: {str(e)}") 