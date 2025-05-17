from fastapi import APIRouter, Depends, HTTPException
from infrastructure.adapters.sources.google_drive_adapter import GoogleDriveAdapter, GoogleDriveError
from infrastructure.adapters.auth.google_auth import GoogleAuthService
from .dependencies import auth_service
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/drive/ebooks",
    tags=["Ebooks"]
)

def get_ebook_source() -> GoogleDriveAdapter:
    """Provider pour la source des ebooks"""
    return GoogleDriveAdapter(auth_service)

@router.get("/{ebook_id}")
async def get_ebook(
    ebook_id: str,
    ebook_source: GoogleDriveAdapter = Depends(get_ebook_source)
):
    """Récupère un ebook spécifique"""
    try:
        logger.info(f"Tentative de récupération de l'ebook {ebook_id}")
        ebook = await ebook_source.get_ebook(ebook_id)
        if not ebook:
            logger.warning(f"Ebook {ebook_id} non trouvé")
            raise HTTPException(status_code=404, detail="Ebook non trouvé")
        logger.info(f"Ebook {ebook_id} récupéré avec succès")
        return ebook
    except GoogleDriveError as e:
        logger.error(f"Erreur Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur inattendue: {str(e)}") 