import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from backoffice.domain.entities.ebook import EbookStatus
from backoffice.domain.entities.pagination import PaginationParams
from backoffice.domain.usecases.approve_ebook import ApproveEbookUseCase
from backoffice.domain.usecases.get_ebooks import GetEbooksUseCase
from backoffice.domain.usecases.get_stats import GetStatsUseCase
from backoffice.domain.usecases.reject_ebook import RejectEbookUseCase
from backoffice.domain.usecases.submit_ebook_for_validation import SubmitEbookForValidationUseCase
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
    elif status == "pending":
        ebook_status = EbookStatus.PENDING
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
    elif status == "pending":
        ebook_status = EbookStatus.PENDING
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
) -> Response:
    """Crée un nouvel ebook de coloriage (coloring book only)."""
    logger.info(f"Creating coloring book - Theme: {theme_id}, Audience: {audience}")
    try:
        # Only coloring books are supported
        if ebook_type != "coloring":
            raise ValueError(f"Type '{ebook_type}' non supporté. Seul 'coloring' est disponible.")

        # Handle theme-based generation for coloring books
        theme_repository = ThemeRepository()

        # ✨ NEW ARCHITECTURE: Use hexagonal architecture for coloring book generation
        from backoffice.application.ebook_generation_facade import EbookGenerationFacade
        from backoffice.domain.entities.generation_request import AgeGroup as NewAgeGroup

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

        pages_count = number_of_pages or 8

        logger.info("🎨 Generating coloring book via NEW ARCHITECTURE")
        logger.info(f"   Theme: {theme.label} ({theme.blocks.subject})")
        logger.info(f"   Age group: {new_age_group.value}")
        logger.info(f"   Pages: {pages_count}")

        # 🚀 Call new architecture facade
        generation_result = await EbookGenerationFacade.generate_coloring_book(
            title=title or f"Livre de coloriage - {theme.label}",
            theme=theme.blocks.subject,
            age_group=new_age_group,
            page_count=pages_count,
            seed=None,
        )

        logger.info(f"✅ NEW ARCHITECTURE: PDF generated at {generation_result.pdf_uri}")
        logger.info(f"   Total pages: {len(generation_result.pages_meta)}")

        # 📤 Upload PDF to Google Drive
        import pathlib

        pdf_path = pathlib.Path(generation_result.pdf_uri.replace("file://", ""))
        logger.info(f"📤 Uploading PDF to Google Drive: {pdf_path}")

        # Get file storage adapter
        file_storage = factory.get_file_storage()
        drive_id = None
        drive_preview_url = None

        if file_storage.is_available():
            try:
                # Read PDF bytes
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                # Upload to Drive
                filename = f"{title or 'coloring_book'}_{theme_id}.pdf"
                upload_result = await file_storage.upload_ebook(
                    file_bytes=pdf_bytes,
                    filename=filename,
                    metadata={
                        "title": title or f"Livre de coloriage - {theme.label}",
                        "author": author or "Auteur Inconnu",
                        "theme_id": theme_id,
                        "audience": audience,
                        "pages": str(pages_count),
                    },
                )

                # GoogleDriveStorageAdapter returns "storage_id" and "storage_url"
                drive_id = upload_result.get("storage_id")
                drive_preview_url = upload_result.get("storage_url")

                logger.info(f"✅ PDF uploaded to Drive: {drive_id}")
                logger.info(f"   Preview URL: {drive_preview_url}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to upload to Drive: {e}")
        else:
            logger.warning("⚠️ Google Drive not available, skipping upload")

        # 🎯 NEW ARCHITECTURE SHORTCUT: PDF is already generated, save ebook directly
        import base64

        from backoffice.domain.entities.ebook import Ebook, EbookStatus

        # Use Drive preview URL if available, otherwise fall back to local file
        final_preview_url = drive_preview_url if drive_id else generation_result.pdf_uri

        # Build structure_json with pages metadata for regeneration
        structure_json = {
            "pages_meta": [
                {
                    "page_number": page_meta.page_number,
                    "title": page_meta.title,
                    "image_format": page_meta.format,
                    "image_data_base64": base64.b64encode(page_meta.image_data).decode(),
                }
                for page_meta in generation_result.pages_meta
            ]
        }

        # Create ebook entity directly with generated PDF
        # Note: pdf_path and other legacy fields removed from Ebook entity
        new_ebook = Ebook(
            id=0,  # Will be set by repository
            title=title or f"Livre de coloriage - {theme.label}",
            author=author or "Auteur Inconnu",
            created_at=None,  # Will be set by repository
            status=EbookStatus.PENDING,
            preview_url=final_preview_url,  # Google Drive preview URL
            drive_id=drive_id,  # Google Drive file ID
            config=None,  # No config needed for new arch
            theme_id=theme_id,
            theme_version=theme_repository.get_theme_version(theme_id),
            audience=audience,
            structure_json=structure_json,  # Store pages for regeneration
        )

        # Save to repository
        ebook_repo = factory.get_ebook_repository()
        saved_ebook = await ebook_repo.create(new_ebook)
        logger.info(f"✅ Ebook saved to database: ID={saved_ebook.id}")

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
        approve_usecase = ApproveEbookUseCase(ebook_repo)
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


@router.post("/ebooks/{ebook_id}/submit")
async def submit_ebook_for_validation(
    ebook_id: int, request: Request, factory: RepositoryFactoryDep
) -> Response:
    """Submit an ebook for validation (DRAFT → PENDING transition)."""
    try:
        ebook_repo = factory.get_ebook_repository()
        submit_usecase = SubmitEbookForValidationUseCase(ebook_repo)
        updated_ebook = await submit_usecase.execute(ebook_id)

        ebook_data = {
            "id": updated_ebook.id,
            "title": updated_ebook.title,
            "author": updated_ebook.author,
            "created_at": updated_ebook.created_at,
            "status": updated_ebook.status.value,
            "preview_url": updated_ebook.preview_url,
            "drive_id": updated_ebook.drive_id,
        }

        return templates.TemplateResponse(
            "partials/ebooks_table_row.html",
            {"request": request, "ebook": type("Ebook", (), ebook_data)()},
        )
    except ValueError as e:
        logger.warning(f"Validation error submitting ebook {ebook_id}: {str(e)}")
        error_html = f"""<div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            {str(e)}
        </div>"""
        return HTMLResponse(content=error_html, status_code=400)
    except Exception as e:
        logger.error(f"Unexpected error submitting ebook {ebook_id}: {str(e)}", exc_info=True)
        error_html = """<div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            Erreur lors de la soumission de l'ebook. Veuillez réessayer.
        </div>"""
        return HTMLResponse(content=error_html, status_code=500)
