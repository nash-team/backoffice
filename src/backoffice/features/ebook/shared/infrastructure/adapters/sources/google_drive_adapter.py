import logging
from datetime import datetime
from io import BytesIO

from googleapiclient.http import MediaIoBaseUpload

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.infrastructure.adapters.auth.google_auth import GoogleAuthService

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

    async def get_ebook(self, source_id: str) -> Ebook | None:
        """Récupère un ebook spécifique depuis Google Drive"""
        try:
            logger.info(f"Tentative de récupération du fichier {source_id} depuis Google Drive")
            file = self.drive_service.files().get(fileId=source_id, fields="id, name, createdTime").execute()

            logger.info(f"Fichier {source_id} récupéré avec succès")

            # Construction de l'URL d'aperçu Google Drive
            preview_url = f"https://drive.google.com/file/d/{source_id}/preview"

            return Ebook(
                id=0,  # L'ID sera généré par la base de données
                title=file["name"],
                author="",  # À remplir plus tard
                created_at=datetime.fromisoformat(file["createdTime"].replace("Z", "+00:00")),
                status=EbookStatus.DRAFT,
                drive_id=file["id"],
                preview_url=preview_url,  # URL d'aperçu Google Drive
            )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'ebook {source_id}: {str(e)}")
            raise GoogleDriveError(f"Erreur lors de la récupération de l'ebook: {str(e)}") from e

    async def upload_ebook(self, title: str, content: str, author: str = "Assistant IA") -> dict:
        """Upload un ebook généré vers Google Drive"""
        try:
            logger.info(f"Upload de l'ebook '{title}' vers Google Drive")

            # Créer le contenu du fichier (markdown/text)
            file_content = f"""# {title}

**Auteur:** {author}
**Date de création:** {datetime.now().strftime('%d/%m/%Y')}

---

{content}
"""

            # Créer le média upload
            media = MediaIoBaseUpload(BytesIO(file_content.encode("utf-8")), mimetype="text/plain", resumable=True)

            # Métadonnées du fichier
            file_metadata = {
                "name": f"{title}.txt",
                "parents": [],  # Racine du Drive, ou spécifier un dossier
            }

            # Upload vers Google Drive
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

            drive_id = file.get("id")

            # Rendre le fichier accessible publiquement
            permission = {"role": "reader", "type": "anyone"}
            self.drive_service.permissions().create(fileId=drive_id, body=permission).execute()

            preview_url = f"https://drive.google.com/file/d/{drive_id}/preview"

            logger.info(f"Ebook uploadé avec succès et rendu public. Drive ID: {drive_id}")

            return {
                "title": title,
                "author": author,
                "drive_id": drive_id,
                "preview_url": preview_url,
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'upload de l'ebook '{title}': {str(e)}")
            raise GoogleDriveError(f"Erreur lors de l'upload de l'ebook: {str(e)}") from e

    async def upload_pdf_ebook(self, title: str, pdf_bytes: bytes, author: str = "Assistant IA") -> dict:
        """Upload un ebook PDF vers Google Drive"""
        try:
            logger.info(f"Upload du PDF '{title}' vers Google Drive")

            # Créer le média upload pour PDF
            media = MediaIoBaseUpload(BytesIO(pdf_bytes), mimetype="application/pdf", resumable=True)

            # Métadonnées du fichier
            file_metadata = {
                "name": f"{title}.pdf",
                "description": f"Ebook généré par l'Assistant IA - Auteur: {author}",
                "parents": [],  # Racine du Drive, ou spécifier un dossier
            }

            # Upload vers Google Drive
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

            drive_id = file.get("id")

            # Rendre le fichier accessible publiquement
            permission = {"role": "reader", "type": "anyone"}
            self.drive_service.permissions().create(fileId=drive_id, body=permission).execute()

            preview_url = f"https://drive.google.com/file/d/{drive_id}/preview"

            logger.info(f"PDF uploadé avec succès et rendu public. Drive ID: {drive_id}")

            return {
                "title": title,
                "author": author,
                "drive_id": drive_id,
                "preview_url": preview_url,
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'upload du PDF '{title}': {str(e)}")
            raise GoogleDriveError(f"Erreur lors de l'upload du PDF: {str(e)}") from e

    async def update_pdf_ebook(self, file_id: str, pdf_bytes: bytes) -> dict:
        """Update an existing PDF ebook in Google Drive"""
        try:
            logger.info(f"Updating PDF in Google Drive: {file_id}")

            # Create media upload for PDF
            media = MediaIoBaseUpload(BytesIO(pdf_bytes), mimetype="application/pdf", resumable=True)

            # Update the file content
            updated_file = self.drive_service.files().update(fileId=file_id, media_body=media, fields="id,name").execute()

            drive_id = updated_file.get("id")
            preview_url = f"https://drive.google.com/file/d/{drive_id}/preview"

            logger.info(f"PDF updated successfully. Drive ID: {drive_id}")

            return {
                "drive_id": drive_id,
                "preview_url": preview_url,
            }

        except Exception as e:
            logger.error(f"Error updating PDF in Google Drive: {str(e)}")
            raise GoogleDriveError(f"Error updating PDF: {str(e)}") from e
