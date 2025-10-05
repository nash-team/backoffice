"""Routes for ebook lifecycle feature.

This module provides HTTP endpoints for ebook lifecycle management:
approval, rejection, and statistics.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response

from backoffice.features.ebook_lifecycle.domain.usecases.approve_ebook_usecase import (
    ApproveEbookUseCase,
)
from backoffice.features.ebook_lifecycle.domain.usecases.get_stats_usecase import GetStatsUseCase
from backoffice.features.ebook_lifecycle.domain.usecases.reject_ebook_usecase import (
    RejectEbookUseCase,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus
from backoffice.features.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.shared.presentation.routes.templates import templates

RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api/dashboard", tags=["Ebook Lifecycle"])
logger = logging.getLogger(__name__)


@router.get("/stats")
async def get_stats(request: Request, factory: RepositoryFactoryDep) -> Response:
    """Get ebook statistics (counts by status).

    Returns:
        HTML response with stats partial (for HTMX)
    """
    ebook_repo = factory.get_ebook_repository()
    get_stats_usecase = GetStatsUseCase(ebook_repo)
    stats = await get_stats_usecase.execute()
    return templates.TemplateResponse("partials/stats.html", {"request": request, "stats": stats})


@router.put("/ebooks/{ebook_id}/approve")
async def approve_ebook(ebook_id: int, request: Request, factory: RepositoryFactoryDep) -> Response:
    """Approve an ebook and upload it to storage.

    Args:
        ebook_id: ID of the ebook to approve
        request: FastAPI request object
        factory: Repository factory for dependency injection

    Returns:
        HTML response with updated ebook table row (for HTMX)
    """
    try:
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()
        event_bus = EventBus()
        approve_usecase = ApproveEbookUseCase(ebook_repo, file_storage, event_bus)
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
    """Reject an ebook during review.

    Args:
        ebook_id: ID of the ebook to reject
        request: FastAPI request object
        factory: Repository factory for dependency injection

    Returns:
        HTML response with updated ebook table row (for HTMX)
    """
    try:
        ebook_repo = factory.get_ebook_repository()
        event_bus = EventBus()
        reject_usecase = RejectEbookUseCase(ebook_repo, event_bus)
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
