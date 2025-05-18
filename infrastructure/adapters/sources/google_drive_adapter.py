import logging
from datetime import datetime
from typing import Optional

from domain.entities.ebook import Ebook, EbookStatus
from infrastructure.adapters.auth.google_auth import GoogleAuthService

logger = logging.getLogger(__name__)


class GoogleDriveError(Exception):
    """Exception levée en cas d'erreur avec Google Drive"""

    pass


class GoogleDriveAdapter:
    """Adaptateur pour récupérer les ebooks depuis Google Drive"""

    def __init__(self, auth_service: GoogleAuthService):
        self.auth_service = auth_service
        self.drive_service = auth_service.get_drive_service()
        logger.info("GoogleDriveAdapter initialisé")

    async def get_ebook(self, source_id: str) -> Optional[Ebook]:
        """Récupère un ebook spécifique depuis Google Drive"""
        try:
            logger.info(f"Tentative de récupération du fichier {source_id} depuis Google Drive")
            file = (
                self.drive_service.files()
                .get(fileId=source_id, fields="id, name, createdTime")
                .execute()
            )

            logger.info(f"Fichier {source_id} récupéré avec succès")

            # Construction de l'URL d'aperçu Google Drive
            preview_url = f"https://drive.google.com/file/d/{source_id}/preview"

            return Ebook(
                id=0,  # L'ID sera généré par la base de données
                title=file["name"],
                author="",  # À remplir plus tard
                created_at=datetime.fromisoformat(file["createdTime"].replace("Z", "+00:00")),
                status=EbookStatus.PENDING,
                drive_id=file["id"],
                preview_url=preview_url,  # URL d'aperçu Google Drive
            )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'ebook {source_id}: {str(e)}")
            raise GoogleDriveError(f"Erreur lors de la récupération de l'ebook: {str(e)}") from e
