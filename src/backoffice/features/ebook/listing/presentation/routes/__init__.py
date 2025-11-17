"""Routes for ebook listing feature."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from backoffice.features.ebook.listing.domain.usecases.get_ebooks import GetEbooksUseCase
from backoffice.features.ebook.shared.domain.entities.ebook import EbookStatus
from backoffice.features.ebook.shared.domain.entities.pagination import PaginationParams
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.shared.presentation.routes.templates import templates

# Type alias for dependency injection
RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api/dashboard", tags=["Ebook Listing"])
logger = logging.getLogger(__name__)


@router.get("/ebooks")
async def get_ebooks(
    request: Request,
    factory: RepositoryFactoryDep,
    status: str | None = None,
    page: int = 1,
    size: int = 15,
) -> Response:
    """List ebooks with optional status filter and pagination (HTML response)."""
    try:
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

    # Serialize for template
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
    List ebooks with optional status filter and pagination (JSON response).
    Primarily used for testing and API consumption.
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


@router.get("/ebooks/{ebook_id}/preview")
async def get_ebook_preview_modal(ebook_id: int, request: Request, factory: RepositoryFactoryDep) -> Response:
    """Load ebook preview modal content."""
    try:
        ebook_repo = factory.get_ebook_repository()
        ebook = await ebook_repo.get_by_id(ebook_id)

        if not ebook:
            raise HTTPException(status_code=404, detail=f"Ebook with id {ebook_id} not found")

        return templates.TemplateResponse("partials/ebook_preview_modal.html", {"request": request, "ebook": ebook})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading ebook preview {ebook_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error loading ebook preview") from e


@router.get("/ebooks/{ebook_id}", response_class=HTMLResponse)
async def get_ebook_detail_page(ebook_id: int, request: Request, factory: RepositoryFactoryDep) -> Response:
    """Display dedicated ebook detail page with PDF viewer and actions."""
    try:
        ebook_repo = factory.get_ebook_repository()
        ebook = await ebook_repo.get_by_id(ebook_id)

        if not ebook:
            raise HTTPException(status_code=404, detail=f"Ebook with id {ebook_id} not found")

        return templates.TemplateResponse("ebook_detail.html", {"request": request, "ebook": ebook})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading ebook detail page {ebook_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error loading ebook detail") from e


@router.get("/drive/ebooks/{drive_id}")
async def get_drive_preview_url(drive_id: str) -> Response:
    """Generate Google Drive preview URL for an ebook."""
    preview_url = f"https://drive.google.com/file/d/{drive_id}/preview"
    return Response(content=preview_url, media_type="text/plain")
