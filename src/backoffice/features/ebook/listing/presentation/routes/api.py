"""JSON API routes for ebook listing (React SPA consumption)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backoffice.features.ebook.listing.domain.usecases.get_ebooks import GetEbooksUseCase
from backoffice.features.ebook.shared.domain.entities.ebook import EbookStatus
from backoffice.features.ebook.shared.domain.entities.pagination import PaginationParams
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)

RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api", tags=["Ebook API"])
logger = logging.getLogger(__name__)

_STATUS_MAP = {
    "draft": EbookStatus.DRAFT,
    "approved": EbookStatus.APPROVED,
    "rejected": EbookStatus.REJECTED,
}


@router.get("/ebooks")
async def list_ebooks(
    factory: RepositoryFactoryDep,
    status: str | None = None,
    page: int = 1,
    size: int = 15,
) -> dict:
    """List ebooks with optional status filter and pagination (JSON)."""
    try:
        pagination_params = PaginationParams(page=page, size=size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    ebook_repo = factory.get_ebook_repository()
    use_case = GetEbooksUseCase(ebook_repo)
    ebook_status = _STATUS_MAP.get(status) if status else None

    result = await use_case.execute_paginated(pagination_params, ebook_status)

    return {
        "items": [
            {
                "id": e.id,
                "title": e.title,
                "author": e.author,
                "theme": e.theme_id,
                "audience": e.audience,
                "status": e.status.value,
                "num_pages": e.page_count,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": None,
            }
            for e in result.items
        ],
        "total": result.total_count,
        "page": result.page,
        "per_page": result.size,
        "total_pages": result.total_pages,
    }


@router.get("/ebooks/{ebook_id}")
async def get_ebook_detail(
    ebook_id: int,
    factory: RepositoryFactoryDep,
) -> dict:
    """Get ebook detail with pages_meta (without base64 image_data)."""
    ebook_repo = factory.get_ebook_repository()
    ebook = await ebook_repo.get_by_id(ebook_id)

    if not ebook:
        raise HTTPException(status_code=404, detail=f"Ebook {ebook_id} not found")

    pages_meta = []
    if ebook.structure_json and "pages_meta" in ebook.structure_json:
        for p in ebook.structure_json["pages_meta"]:
            pages_meta.append(
                {
                    "page_number": p.get("page_number", 0),
                    "title": p.get("title", ""),
                    "format": p.get("format", "PNG"),
                    "color_mode": p.get("color_mode", "BLACK_WHITE"),
                }
            )

    return {
        "id": ebook.id,
        "title": ebook.title,
        "author": ebook.author,
        "theme": ebook.theme_id,
        "audience": ebook.audience,
        "status": ebook.status.value,
        "num_pages": ebook.page_count,
        "created_at": ebook.created_at.isoformat() if ebook.created_at else None,
        "updated_at": None,
        "drive_id": ebook.drive_id,
        "pages_meta": pages_meta,
    }
