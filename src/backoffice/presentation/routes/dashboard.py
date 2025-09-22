import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse

from backoffice.domain.entities.ebook import EbookStatus
from backoffice.domain.entities.ebook_theme import EbookType, ExtendedEbookConfig
from backoffice.domain.usecases.create_ebook import CreateEbookUseCase
from backoffice.domain.usecases.get_ebooks import GetEbooksUseCase
from backoffice.domain.usecases.get_stats import GetStatsUseCase
from backoffice.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)

# Import des templates centralisés
from backoffice.presentation.routes.templates import templates

# Type alias pour l'injection de dépendance sécurisée
RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
logger = logging.getLogger(__name__)


@router.get("/stats")
async def get_stats(request: Request, factory: RepositoryFactoryDep) -> Response:
    ebook_repo = factory.get_ebook_repository()
    get_stats_usecase = GetStatsUseCase(ebook_repo)
    stats = await get_stats_usecase.execute()
    return templates.TemplateResponse("partials/stats.html", {"request": request, "stats": stats})


@router.get("/ebooks")
async def get_ebooks(
    request: Request,
    factory: RepositoryFactoryDep,
    status: str | None = None,
) -> Response:
    ebook_repo = factory.get_ebook_repository()
    get_ebooks_usecase = GetEbooksUseCase(ebook_repo)

    ebook_status = None
    if status == "pending":
        ebook_status = EbookStatus.PENDING
    elif status == "validated":
        ebook_status = EbookStatus.VALIDATED
    ebooks = await get_ebooks_usecase.execute(ebook_status)

    # Sérialisation pour le template
    ebooks_data = [
        {
            "id": e.id,
            "title": e.title,
            "author": e.author,
            "created_at": e.created_at,
            "status": e.status.value,
            "drive_id": e.drive_id,
        }
        for e in ebooks
    ]

    return templates.TemplateResponse(
        "partials/ebooks_table.html", {"request": request, "ebooks": ebooks_data}
    )


@router.get("/drive/ebooks/{drive_id}")
async def get_ebook_preview(drive_id: str) -> Response:
    # Simuler une URL de prévisualisation Google Drive
    preview_url = f"https://drive.google.com/file/d/{drive_id}/preview"
    return Response(content=preview_url, media_type="text/plain")


@router.get("/ebooks/new")
async def get_new_ebook_form(request: Request) -> Response:
    """Affiche le formulaire de création d'un nouvel ebook avec sélection de thèmes."""
    logger.info("Loading enhanced ebook form")
    return templates.TemplateResponse("partials/enhanced_ebook_form.html", {"request": request})


@router.post("/ebooks")
async def create_ebook(
    request: Request,
    factory: RepositoryFactoryDep,
    prompt: str = Form(...),
    ebook_type: str = Form(...),
    theme_name: str = Form(None),
    cover_template: str = Form(None),
    toc_template: str = Form(None),
    text_template: str = Form(None),
    image_template: str = Form(None),
    title: str = Form(None),
    author: str = Form("Assistant IA"),
    cover_enabled: bool = Form(True),
    toc: bool = Form(True),
    format: str = Form("pdf"),
) -> Response:
    """Crée un nouvel ebook à partir du prompt et de la configuration."""
    logger.info(
        f"Creating ebook - Type: {ebook_type}, Theme: {theme_name}, " f"Prompt: {prompt[:50]}..."
    )
    try:
        # Valider le type d'ebook
        try:
            parsed_ebook_type = EbookType(ebook_type)
        except ValueError as e:
            raise ValueError(f"Type d'ebook invalide: {ebook_type}") from e

        # Créer la configuration étendue
        extended_config = ExtendedEbookConfig(
            ebook_type=parsed_ebook_type,
            theme_name=theme_name,
            cover_template=cover_template,
            toc_template=toc_template,
            text_template=text_template,
            image_template=image_template,
            cover_enabled=cover_enabled,
            toc=toc,
            format=format,
        )

        # Use case execution
        ebook_repo = factory.get_ebook_repository()
        ebook_processor = factory.get_ebook_processor()

        create_ebook_usecase = CreateEbookUseCase(ebook_repo, ebook_processor)

        # Create new ebook with extended config
        new_ebook = await create_ebook_usecase.execute(
            prompt=prompt,
            config=extended_config,
            title=title,
            ebook_type=ebook_type,
            theme_name=theme_name,
        )
        logger.info(f"Ebook created successfully: {new_ebook.title} (ID: {new_ebook.id})")

        # Get updated ebooks list
        get_ebooks_usecase = GetEbooksUseCase(ebook_repo)
        ebooks = await get_ebooks_usecase.execute()

        # Format response data
        ebooks_data = [
            {
                "id": e.id,
                "title": e.title,
                "author": e.author,
                "created_at": e.created_at,
                "status": e.status.value,
                "drive_id": e.drive_id,
            }
            for e in ebooks
        ]

        response = templates.TemplateResponse(
            "partials/ebooks_table.html", {"request": request, "ebooks": ebooks_data}
        )
        response.headers["HX-Trigger"] = '{"ebook:created": true}'
        return response

    except ValueError as e:
        # Business rule validation error - return OOB error fragment
        logger.warning(f"Validation error in ebook creation: {str(e)}")
        error_html = f"""<div id="ebookFormErrors" hx-swap-oob="true" class="mb-3">
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                {str(e)}
            </div>
        </div>"""
        return HTMLResponse(content=error_html, status_code=400)
    except Exception as e:
        # Generic error handling - return OOB error fragment
        logger.error(f"Unexpected error in ebook creation: {str(e)}", exc_info=True)
        error_html = """<div id="ebookFormErrors" hx-swap-oob="true" class="mb-3">
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Erreur lors de la création de l'ebook. Veuillez réessayer.
            </div>
        </div>"""
        return HTMLResponse(content=error_html, status_code=500)
