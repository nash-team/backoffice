import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException

from backoffice.infrastructure.adapters.sources.google_drive_adapter import (
    GoogleDriveAdapter,
    GoogleDriveError,
)
from backoffice.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.presentation.routes.dependencies import auth_service

# Type alias for dependency injection
RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

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


# New router for ebook operations (regeneration, etc.)
operations_router = APIRouter(prefix="/api/ebooks", tags=["Ebook Operations"])


@operations_router.post("/{ebook_id}/pages/regenerate")
async def regenerate_ebook_page(
    ebook_id: int,
    factory: RepositoryFactoryDep,
    regeneration_request: Annotated[dict, Body(...)],
) -> dict:
    """
    Regenerate a specific page of an ebook.

    Request body:
    {
        "page_type": "cover" | "chapter" | "toc" | "coloring_page",
        "page_index": 0,
        "prompt_override": "optional custom prompt"
    }
    """
    try:
        # Extract request parameters
        page_type = regeneration_request.get("page_type")
        prompt_override = regeneration_request.get("prompt_override")

        if not page_type:
            raise HTTPException(status_code=400, detail="page_type is required")

        # V1: Only cover regeneration supported
        if page_type != "cover":
            raise HTTPException(
                status_code=400,
                detail=f"Only cover regeneration is supported in V1. Got: {page_type}",
            )

        logger.info(f"Regenerating cover for ebook {ebook_id}")

        # Get dependencies from factory
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()

        # Create new architecture services
        from backoffice.domain.cover_generation import CoverGenerationService
        from backoffice.domain.pdf_assembly import PDFAssemblyService
        from backoffice.domain.usecases.regenerate_cover import RegenerateCoverUseCase
        from backoffice.infrastructure.providers.openrouter_cover_provider import (
            OpenRouterCoverProvider,
        )
        from backoffice.infrastructure.providers.weasyprint_assembly_provider import (
            WeasyPrintAssemblyProvider,
        )

        # Initialize services
        cover_provider = OpenRouterCoverProvider()
        cover_service = CoverGenerationService(cover_port=cover_provider)
        assembly_provider = WeasyPrintAssemblyProvider()
        assembly_service = PDFAssemblyService(assembly_port=assembly_provider)

        # Create and execute use case
        regenerate_usecase = RegenerateCoverUseCase(
            ebook_repository=ebook_repo,
            cover_service=cover_service,
            assembly_service=assembly_service,
            file_storage=file_storage,
        )

        updated_ebook = await regenerate_usecase.execute(
            ebook_id=ebook_id,
            prompt_override=prompt_override,
        )

        logger.info(f"Successfully regenerated cover for ebook {ebook_id}")

        return {
            "success": True,
            "message": f"{page_type} regenerated successfully",
            "ebook_id": updated_ebook.id,
            "preview_url": updated_ebook.preview_url,
        }

    except ValueError as e:
        logger.warning(f"Validation error regenerating page for ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"Unexpected error regenerating page for ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error regenerating page. Please try again.",
        ) from e
