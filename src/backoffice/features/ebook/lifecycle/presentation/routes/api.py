"""JSON API routes for ebook lifecycle (React SPA consumption)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backoffice.features.ebook.lifecycle.domain.usecases.approve_ebook_usecase import (
    ApproveEbookUseCase,
)
from backoffice.features.ebook.lifecycle.domain.usecases.get_stats_usecase import GetStatsUseCase
from backoffice.features.ebook.lifecycle.domain.usecases.reject_ebook_usecase import (
    RejectEbookUseCase,
)
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api", tags=["Ebook Lifecycle API"])
logger = logging.getLogger(__name__)


def _ebook_to_dict(ebook) -> dict:
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
    }


@router.get("/stats")
async def get_stats(factory: RepositoryFactoryDep) -> dict:
    """Get ebook statistics (counts by status)."""
    ebook_repo = factory.get_ebook_repository()
    use_case = GetStatsUseCase(ebook_repo)
    stats = await use_case.execute()
    return {
        "draft": stats.draft_ebooks,
        "approved": stats.approved_ebooks,
        "rejected": stats.rejected_ebooks,
    }


@router.put("/ebooks/{ebook_id}/approve")
async def approve_ebook(ebook_id: int, factory: RepositoryFactoryDep) -> dict:
    """Approve an ebook (JSON response)."""
    try:
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()
        event_bus = EventBus()
        use_case = ApproveEbookUseCase(ebook_repo, file_storage, event_bus)
        updated = await use_case.execute(ebook_id)
        return _ebook_to_dict(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/ebooks/{ebook_id}/reject")
async def reject_ebook(ebook_id: int, factory: RepositoryFactoryDep) -> dict:
    """Reject an ebook (JSON response)."""
    try:
        ebook_repo = factory.get_ebook_repository()
        event_bus = EventBus()
        use_case = RejectEbookUseCase(ebook_repo, event_bus)
        updated = await use_case.execute(ebook_id)
        return _ebook_to_dict(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
