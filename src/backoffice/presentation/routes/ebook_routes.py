import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from backoffice.infrastructure.adapters.sources.google_drive_adapter import (
    GoogleDriveAdapter,
    GoogleDriveError,
)
from backoffice.infrastructure.factories.repository_factory import (
    AsyncRepositoryFactory,
    RepositoryFactory,
    get_async_repository_factory,
    get_repository_factory,
)
from backoffice.presentation.routes.dependencies import auth_service

# Type alias for dependency injection
RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]
AsyncRepositoryFactoryDep = Annotated[AsyncRepositoryFactory, Depends(get_async_repository_factory)]

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/drive/ebooks", tags=["Ebooks"])


def get_ebook_source() -> GoogleDriveAdapter:
    """Provider pour la source des ebooks"""
    return GoogleDriveAdapter(auth_service)


# Dépendance au niveau du module
ebook_source_dep = Depends(get_ebook_source)


@router.get("/{ebook_id}")
async def get_ebook(ebook_id: str, ebook_source: GoogleDriveAdapter = ebook_source_dep) -> Any:
    """Récupère un ebook spécifique"""
    try:
        logger.info(f"Tentative de récupération de l'ebook {ebook_id}")
        ebook = await ebook_source.get_ebook(ebook_id)
        if ebook is None:
            logger.warning(f"Ebook {ebook_id} non trouvé")
            raise HTTPException(status_code=404, detail="Ebook non trouvé")
        logger.info(f"Ebook {ebook_id} récupéré avec succès")
        return ebook
    except GoogleDriveError as e:
        logger.error(f"Erreur Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur inattendue: {str(e)}") from e


# LEGACY: operations_router has been migrated to features/ebook_regeneration
# All regeneration endpoints are now in the ebook_regeneration feature
