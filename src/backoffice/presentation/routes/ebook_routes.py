import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException

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


# New router for ebook operations (regeneration, etc.)
operations_router = APIRouter(prefix="/api/ebooks", tags=["Ebook Operations"])


@operations_router.post("/{ebook_id}/pages/regenerate")
async def regenerate_ebook_page(
    ebook_id: int,
    factory: AsyncRepositoryFactoryDep,
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

        # V1: cover, back_cover, and content_page regeneration supported
        if page_type not in ["cover", "back_cover", "content_page"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Only 'cover', 'back_cover', and 'content_page' regeneration supported. "
                    f"Got: {page_type}"
                ),
            )

        logger.info(f"Regenerating {page_type} for ebook {ebook_id}")

        # Get dependencies from factory
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()

        # Create new architecture services
        from backoffice.domain.cover_generation import CoverGenerationService
        from backoffice.domain.pdf_assembly import PDFAssemblyService
        from backoffice.infrastructure.providers.provider_factory import ProviderFactory
        from backoffice.infrastructure.providers.weasyprint_assembly_provider import (
            WeasyPrintAssemblyProvider,
        )

        # Get ebook to determine which provider was used
        ebook = await ebook_repo.get_by_id(ebook_id)
        if not ebook:
            raise HTTPException(status_code=404, detail=f"Ebook {ebook_id} not found")

        # Setup event-driven cost tracking
        request_id = f"regenerate-{page_type}-{ebook_id}"
        track_usage_usecase = factory.get_track_token_usage_usecase()

        # Create providers with event-driven tracking
        cover_provider = ProviderFactory.create_cover_provider(
            track_usage_usecase=track_usage_usecase, request_id=request_id
        )
        cover_service = CoverGenerationService(cover_port=cover_provider)
        assembly_provider = WeasyPrintAssemblyProvider()
        assembly_service = PDFAssemblyService(assembly_port=assembly_provider)

        # Choose the appropriate use case based on page_type
        from backoffice.domain.usecases.regenerate_back_cover import (
            RegenerateBackCoverUseCase,
        )
        from backoffice.domain.usecases.regenerate_content_page import (
            RegenerateContentPageUseCase,
        )
        from backoffice.domain.usecases.regenerate_cover import RegenerateCoverUseCase

        if page_type == "cover":
            regenerate_usecase: (
                RegenerateCoverUseCase | RegenerateBackCoverUseCase | RegenerateContentPageUseCase
            ) = RegenerateCoverUseCase(
                ebook_repository=ebook_repo,
                cover_service=cover_service,
                assembly_service=assembly_service,
                file_storage=file_storage,
            )
        elif page_type == "back_cover":
            regenerate_usecase = RegenerateBackCoverUseCase(
                ebook_repository=ebook_repo,
                cover_service=cover_service,
                assembly_service=assembly_service,
                file_storage=file_storage,
            )
        else:  # content_page
            page_index = regeneration_request.get("page_index")
            if page_index is None:
                raise HTTPException(
                    status_code=400, detail="page_index is required for content_page regeneration"
                )

            # Create page service for content page generation
            from backoffice.domain.page_generation import ContentPageGenerationService

            page_provider = ProviderFactory.create_content_page_provider(
                track_usage_usecase=track_usage_usecase, request_id=request_id
            )
            page_service = ContentPageGenerationService(page_port=page_provider)

            regenerate_usecase = RegenerateContentPageUseCase(
                ebook_repository=ebook_repo,
                page_service=page_service,
                assembly_service=assembly_service,
                file_storage=file_storage,
            )

        # Execute with appropriate parameters
        if page_type == "content_page":
            updated_ebook = await regenerate_usecase.execute(
                ebook_id=ebook_id,
                page_index=page_index,
                prompt_override=prompt_override,
            )
        else:
            updated_ebook = await regenerate_usecase.execute(
                ebook_id=ebook_id,
                prompt_override=prompt_override,
            )

        # Note: Regeneration costs tracked via generation_costs feature (event-driven)

        logger.info(f"Successfully regenerated {page_type} for ebook {ebook_id}")

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
