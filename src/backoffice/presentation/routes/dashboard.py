import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from backoffice.domain.entities.ebook import EbookStatus
from backoffice.domain.entities.pagination import PaginationParams
from backoffice.domain.errors.error_taxonomy import DomainError
from backoffice.domain.usecases.approve_ebook import ApproveEbookUseCase
from backoffice.domain.usecases.get_ebook_costs import GetEbookCostsUseCase
from backoffice.domain.usecases.get_ebooks import GetEbooksUseCase
from backoffice.domain.usecases.get_stats import GetStatsUseCase
from backoffice.domain.usecases.reject_ebook import RejectEbookUseCase
from backoffice.infrastructure.adapters.theme_repository import ThemeRepository
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
    page: int = 1,
    size: int = 15,
) -> Response:
    try:
        # Validate and create pagination parameters
        pagination_params = PaginationParams(page=page, size=size)
    except ValueError as e:
        return HTMLResponse(content=f"Invalid pagination parameters: {e}", status_code=400)

    ebook_repo = factory.get_ebook_repository()
    get_ebooks_usecase = GetEbooksUseCase(ebook_repo)

    ebook_status = None
    if status == "draft":
        ebook_status = EbookStatus.DRAFT
    elif status == "approved":
        ebook_status = EbookStatus.APPROVED
    elif status == "rejected":
        ebook_status = EbookStatus.REJECTED

    # Get paginated results
    paginated_result = await get_ebooks_usecase.execute_paginated(pagination_params, ebook_status)

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
        for e in paginated_result.items
    ]

    # Prepare pagination data for template
    pagination_data = {
        "current_page": paginated_result.page,
        "total_pages": paginated_result.total_pages,
        "total_count": paginated_result.total_count,
        "has_next": paginated_result.has_next,
        "has_previous": paginated_result.has_previous,
        "next_page": paginated_result.next_page,
        "previous_page": paginated_result.previous_page,
        "start_item": paginated_result.start_item,
        "end_item": paginated_result.end_item,
        "page_size": paginated_result.size,
    }

    return templates.TemplateResponse(
        "partials/ebooks_table.html",
        {
            "request": request,
            "ebooks": ebooks_data,
            "pagination": pagination_data,
            "current_status": status,
        },
    )


@router.get("/ebooks.json")
async def get_ebooks_json(
    factory: RepositoryFactoryDep,
    status: str | None = None,
    page: int = 1,
    size: int = 15,
) -> dict:
    """
    JSON endpoint for ebooks - primarily for testing.
    Returns the same data as the HTML endpoint but in JSON format.
    """
    try:
        pagination_params = PaginationParams(page=page, size=size)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pagination parameters: {e}",
        ) from e

    ebook_repo = factory.get_ebook_repository()
    get_ebooks_usecase = GetEbooksUseCase(ebook_repo)

    ebook_status = None
    if status == "draft":
        ebook_status = EbookStatus.DRAFT
    elif status == "approved":
        ebook_status = EbookStatus.APPROVED
    elif status == "rejected":
        ebook_status = EbookStatus.REJECTED

    paginated_result = await get_ebooks_usecase.execute_paginated(pagination_params, ebook_status)

    return {
        "ebooks": [
            {
                "id": e.id,
                "title": e.title,
                "author": e.author,
                "created_at": e.created_at.strftime("%d/%m/%Y") if e.created_at else None,
                "status": e.status.value,
                "drive_id": e.drive_id,
            }
            for e in paginated_result.items
        ],
        "pagination": {
            "current_page": paginated_result.page,
            "total_pages": paginated_result.total_pages,
            "total_count": paginated_result.total_count,
            "has_next": paginated_result.has_next,
            "has_previous": paginated_result.has_previous,
            "start_item": paginated_result.start_item,
            "end_item": paginated_result.end_item,
            "page_size": paginated_result.size,
        },
    }


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
    ebook_type: str = Form("coloring"),
    theme_id: str = Form(...),  # Required
    audience: str = Form(...),  # Required
    title: str = Form(None),
    author: str = Form("Assistant IA"),
    number_of_pages: int = Form(8),  # Default 8 pages
    preview_mode: bool = Form(False),  # Preview mode (3 images) vs Production (26 images)
) -> Response:
    """Crée un nouvel ebook de coloriage (coloring book only)."""
    logger.info(f"Creating coloring book - Theme: {theme_id}, Audience: {audience}")
    try:
        # Only coloring books are supported
        if ebook_type != "coloring":
            raise ValueError(f"Type '{ebook_type}' non supporté. Seul 'coloring' est disponible.")

        # Handle theme-based generation for coloring books
        theme_repository = ThemeRepository()

        # ✨ NEW ARCHITECTURE: Use UseCase + Strategy pattern
        import uuid

        from backoffice.application.strategies.strategy_factory import StrategyFactory
        from backoffice.domain.entities.generation_request import (
            AgeGroup as NewAgeGroup,
            EbookType,
            GenerationRequest,
        )
        from backoffice.domain.usecases.create_ebook import CreateEbookUseCase

        # Validate required parameters
        if not theme_id:
            raise ValueError("Theme ID is required for coloring books")
        if not audience:
            raise ValueError("Audience is required for coloring books")

        # Load theme info
        logger.info(f"Loading theme with ID: {theme_id}")
        theme = theme_repository.get_theme_by_id(theme_id)

        # Map form age values to enum values
        age_mapping = {
            "3-5": "2-4",  # TODDLER
            "6-8": "6-8",  # EARLY_ELEMENTARY
            "9-12": "8-12",  # ELEMENTARY
        }

        mapped_audience = age_mapping.get(audience, audience)
        new_age_group = NewAgeGroup(mapped_audience)

        # Convert preview_mode string to boolean (Form sends "true"/"false" as strings)
        is_preview = str(preview_mode).lower() in ("true", "1", "yes")

        # Preview mode: 1 page (+ cover + back cover = 3 images)
        # Production mode: use number_of_pages (default 24)
        pages_count = 1 if is_preview else (number_of_pages or 24)

        mode_label = "PREVIEW" if is_preview else "PRODUCTION"
        logger.info(f"🎨 Generating coloring book via UseCase + Strategy ({mode_label} MODE)")
        logger.info(f"   Theme: {theme.label} ({theme.blocks.subject})")
        logger.info(f"   Age group: {new_age_group.value}")
        logger.info(f"   Pages: {pages_count}")

        # Create generation request
        request_id = str(uuid.uuid4())
        generation_request = GenerationRequest(
            title=title or f"Coloring Book - {theme.label}",  # English format
            theme=theme_id,  # Use theme ID for prompt template matching
            age_group=new_age_group,
            ebook_type=EbookType.COLORING,
            page_count=pages_count,
            request_id=request_id,
            seed=None,
        )

        # Create strategy and use case with dependencies
        strategy = StrategyFactory.create_strategy(EbookType.COLORING, request_id=request_id)
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()

        create_ebook_usecase = CreateEbookUseCase(
            ebook_repository=ebook_repo,
            generation_strategy=strategy,
            file_storage=file_storage,
        )

        # Execute use case
        await create_ebook_usecase.execute(generation_request, is_preview=is_preview)

        # Get updated ebooks list for response
        from backoffice.domain.entities.pagination import PaginationParams
        from backoffice.domain.usecases.get_ebooks import GetEbooksUseCase

        get_ebooks_usecase = GetEbooksUseCase(ebook_repo)
        pagination_params = PaginationParams(page=1, size=15)
        paginated_result = await get_ebooks_usecase.execute_paginated(pagination_params)

        ebooks_data = [
            {
                "id": e.id,
                "title": e.title,
                "author": e.author,
                "created_at": e.created_at,
                "status": e.status.value,
                "drive_id": e.drive_id,
            }
            for e in paginated_result.items
        ]

        pagination_data = {
            "current_page": paginated_result.page,
            "total_pages": paginated_result.total_pages,
            "total_count": paginated_result.total_count,
            "has_next": paginated_result.has_next,
            "has_previous": paginated_result.has_previous,
            "next_page": paginated_result.next_page,
            "previous_page": paginated_result.previous_page,
            "start_item": paginated_result.start_item,
            "end_item": paginated_result.end_item,
            "page_size": paginated_result.size,
        }

        response = templates.TemplateResponse(
            "partials/ebooks_table.html",
            {
                "request": request,
                "ebooks": ebooks_data,
                "pagination": pagination_data,
                "current_status": None,
            },
        )
        # Trigger HTMX event to refresh stats
        response.headers["HX-Trigger"] = '{"ebookCreated": true}'
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
        # Extract user-friendly error message from exception chain
        logger.error(f"Unexpected error in ebook creation: {str(e)}", exc_info=True)

        # Extract the last segment after the last colon (the most specific error message)
        error_message = str(e)
        parts = error_message.split(": ")
        display_message = (
            parts[-1] if parts else "Erreur lors de la création de l'ebook. Veuillez réessayer."
        )

        logger.info(f"Returning error message to frontend: {display_message}")

        error_html = f"""<div id="ebookFormErrors" hx-swap-oob="true" class="mb-3">
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                {display_message}
            </div>
        </div>"""
        return HTMLResponse(content=error_html, status_code=500)


@router.put("/ebooks/{ebook_id}/approve")
async def approve_ebook(ebook_id: int, request: Request, factory: RepositoryFactoryDep) -> Response:
    """Approve an ebook and return the updated table row."""
    try:
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()
        approve_usecase = ApproveEbookUseCase(ebook_repo, file_storage)
        updated_ebook = await approve_usecase.execute(ebook_id)

        ebook_data = {
            "id": updated_ebook.id,
            "title": updated_ebook.title,
            "author": updated_ebook.author,
            "created_at": updated_ebook.created_at,
            "status": updated_ebook.status.value,
            "drive_id": updated_ebook.drive_id,
        }

        return templates.TemplateResponse(
            "partials/ebooks_table_row.html", {"request": request, "ebook": ebook_data}
        )
    except ValueError as e:
        logger.warning(f"Validation error approving ebook {ebook_id}: {str(e)}")
        error_html = f"""<div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            {str(e)}
        </div>"""
        return HTMLResponse(content=error_html, status_code=400)
    except Exception as e:
        logger.error(f"Unexpected error approving ebook {ebook_id}: {str(e)}", exc_info=True)
        error_html = """<div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            Erreur lors de l'approbation de l'ebook. Veuillez réessayer.
        </div>"""
        return HTMLResponse(content=error_html, status_code=500)


@router.put("/ebooks/{ebook_id}/reject")
async def reject_ebook(ebook_id: int, request: Request, factory: RepositoryFactoryDep) -> Response:
    """Reject an ebook and return the updated table row."""
    try:
        ebook_repo = factory.get_ebook_repository()
        reject_usecase = RejectEbookUseCase(ebook_repo)
        updated_ebook = await reject_usecase.execute(ebook_id)

        ebook_data = {
            "id": updated_ebook.id,
            "title": updated_ebook.title,
            "author": updated_ebook.author,
            "created_at": updated_ebook.created_at,
            "status": updated_ebook.status.value,
            "drive_id": updated_ebook.drive_id,
        }

        return templates.TemplateResponse(
            "partials/ebooks_table_row.html", {"request": request, "ebook": ebook_data}
        )
    except ValueError as e:
        logger.warning(f"Validation error rejecting ebook {ebook_id}: {str(e)}")
        error_html = f"""<div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            {str(e)}
        </div>"""
        return HTMLResponse(content=error_html, status_code=400)
    except Exception as e:
        logger.error(f"Unexpected error rejecting ebook {ebook_id}: {str(e)}", exc_info=True)
        error_html = """<div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            Erreur lors du rejet de l'ebook. Veuillez réessayer.
        </div>"""
        return HTMLResponse(content=error_html, status_code=500)


@router.get("/ebooks/{ebook_id}/preview")
async def get_ebook_preview_modal(
    ebook_id: int, request: Request, factory: RepositoryFactoryDep
) -> Response:
    """Load ebook preview modal content."""
    try:
        ebook_repo = factory.get_ebook_repository()
        ebook = await ebook_repo.get_by_id(ebook_id)

        if not ebook:
            raise HTTPException(status_code=404, detail=f"Ebook with id {ebook_id} not found")

        return templates.TemplateResponse(
            "partials/ebook_preview_modal.html", {"request": request, "ebook": ebook}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading ebook preview {ebook_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error loading ebook preview") from e


@router.get("/ebooks/{ebook_id}/pdf")
async def get_ebook_pdf(ebook_id: int, factory: RepositoryFactoryDep) -> Response:
    """Serve PDF bytes for DRAFT ebooks (before Drive upload)."""
    try:
        from fastapi.responses import Response as FastAPIResponse

        ebook_repo = factory.get_ebook_repository()
        ebook = await ebook_repo.get_by_id(ebook_id)

        if not ebook:
            raise HTTPException(status_code=404, detail=f"Ebook with id {ebook_id} not found")

        # Get PDF bytes from repository
        pdf_bytes = await ebook_repo.get_ebook_bytes(ebook_id)

        if not pdf_bytes:
            raise HTTPException(
                status_code=404, detail="PDF not found - may have been deleted after approval"
            )

        # Return PDF with proper headers
        return FastAPIResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{ebook.title}.pdf"',
                "Cache-Control": "public, max-age=3600",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving PDF for ebook {ebook_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error serving PDF") from e


@router.get("/ebooks/{ebook_id}/export-kdp")
async def export_ebook_to_kdp(
    ebook_id: int, factory: RepositoryFactoryDep, preview: bool = False
) -> Response:
    """Export an approved ebook to Amazon KDP paperback format.

    Args:
        ebook_id: ID of the ebook
        preview: If True, display inline (allows DRAFT); if False, download (requires APPROVED)
    """
    try:
        from fastapi.responses import Response as FastAPIResponse

        from backoffice.domain.usecases.export_to_kdp import ExportToKDPUseCase

        ebook_repo = factory.get_ebook_repository()
        export_usecase = ExportToKDPUseCase(ebook_repo)

        # Execute export (preview_mode=True allows DRAFT, False requires APPROVED)
        kdp_pdf_bytes = await export_usecase.execute(ebook_id, preview_mode=preview)

        # Get ebook for filename
        ebook = await ebook_repo.get_by_id(ebook_id)
        filename = f"{ebook.title}_KDP.pdf" if ebook else f"ebook_{ebook_id}_KDP.pdf"

        # Return PDF (inline for preview, attachment for download)
        disposition = "inline" if preview else "attachment"
        return FastAPIResponse(
            content=kdp_pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "Cache-Control": "no-cache",
            },
        )
    except DomainError as e:
        logger.warning(f"Domain error exporting ebook {ebook_id} to KDP: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotImplementedError as e:
        logger.warning(f"KDP export not yet implemented for ebook {ebook_id}")
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error exporting ebook {ebook_id} to KDP: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error exporting to KDP format. Please try again.",
        ) from e


@router.get("/costs")
async def get_costs_page(request: Request, factory: RepositoryFactoryDep) -> Response:
    """Display ebook generation costs page.

    Args:
        request: FastAPI request object
        factory: Repository factory for data access

    Returns:
        Rendered costs page template
    """
    try:
        ebook_repo = factory.get_ebook_repository()
        get_costs_usecase = GetEbookCostsUseCase(ebook_repo)
        cost_summaries = await get_costs_usecase.execute()

        # Calculate total cost
        from decimal import Decimal

        total_cost = sum((s.cost for s in cost_summaries), Decimal("0"))

        return templates.TemplateResponse(
            "costs.html",
            {
                "request": request,
                "cost_summaries": cost_summaries,
                "total_cost": total_cost,
            },
        )
    except Exception as e:
        logger.error(f"Error loading costs page: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error loading costs page") from e


# Route removed: submit_ebook_for_validation (PENDING status no longer exists)
