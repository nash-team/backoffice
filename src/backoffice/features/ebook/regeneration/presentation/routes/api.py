"""JSON API routes for ebook regeneration feature (React frontend)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from backoffice.features.ebook.regeneration.domain.entities.page_type import PageType
from backoffice.features.ebook.regeneration.domain.usecases.add_new_pages import AddNewPagesUseCase
from backoffice.features.ebook.regeneration.domain.usecases.complete_ebook_pages import CompleteEbookPagesUseCase
from backoffice.features.ebook.regeneration.domain.usecases.regenerate_back_cover import RegenerateBackCoverUseCase
from backoffice.features.ebook.regeneration.domain.usecases.regenerate_content_page import RegenerateContentPageUseCase
from backoffice.features.ebook.regeneration.domain.usecases.regenerate_cover import RegenerateCoverUseCase
from backoffice.features.ebook.regeneration.presentation.routes.cover_routes import (
    router as cover_router,
)
from backoffice.features.ebook.regeneration.presentation.routes.dependencies import (
    create_cover_service,
    create_page_service,
    create_regeneration_service,
)
from backoffice.features.ebook.regeneration.presentation.routes.page_routes import (
    router as page_router,
)
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api/ebooks", tags=["Ebook Regeneration API"])
logger = logging.getLogger(__name__)

# Include cover & page sub-routers (preview-regenerate, edit, apply-edit, page data)
router.include_router(cover_router)
router.include_router(page_router)


@router.post("/{ebook_id}/regenerate")
async def regenerate_pages(
    ebook_id: int,
    factory: RepositoryFactoryDep,
    body: Annotated[dict, Body(...)],
) -> dict:
    """Regenerate cover, back cover, or selected content pages."""
    try:
        page_type_str = body.get("page_type")
        page_indices = body.get("page_indices")

        if not page_type_str:
            raise HTTPException(status_code=400, detail="page_type is required")

        try:
            page_type = PageType(page_type_str)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid page_type: {page_type_str}") from e

        ebook_repo = factory.get_ebook_repository()
        event_bus = EventBus()
        regeneration_service = create_regeneration_service(factory)

        if page_type == PageType.COVER:
            cover_service = create_cover_service()
            cover_uc = RegenerateCoverUseCase(
                ebook_repository=ebook_repo,
                cover_service=cover_service,
                regeneration_service=regeneration_service,
                event_bus=event_bus,
            )
            updated_ebook = await cover_uc.execute(ebook_id=ebook_id)
            message = "Cover regenerated"

        elif page_type == PageType.BACK_COVER:
            cover_service = create_cover_service()
            back_uc = RegenerateBackCoverUseCase(
                ebook_repository=ebook_repo,
                cover_service=cover_service,
                regeneration_service=regeneration_service,
                event_bus=event_bus,
            )
            updated_ebook = await back_uc.execute(ebook_id=ebook_id)
            message = "Back cover regenerated"

        else:
            page_service = create_page_service()
            page_uc = RegenerateContentPageUseCase(
                ebook_repository=ebook_repo,
                page_service=page_service,
                regeneration_service=regeneration_service,
                event_bus=event_bus,
            )

            if not page_indices or not isinstance(page_indices, list):
                raise HTTPException(status_code=400, detail="page_indices is required for content_page")

            for idx in page_indices:
                updated_ebook = await page_uc.execute(ebook_id=ebook_id, page_index=idx)

            message = f"{len(page_indices)} page(s) regenerated"

        return {
            "success": True,
            "message": message,
            "ebook_id": updated_ebook.id,
            "preview_url": updated_ebook.preview_url,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating for ebook {ebook_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error regenerating. Please try again.") from e


@router.post("/{ebook_id}/complete-pages")
async def complete_pages(
    ebook_id: int,
    factory: RepositoryFactoryDep,
    target_pages: int = 24,
) -> dict:
    """Complete ebook with blank pages to reach KDP minimum."""
    try:
        ebook_repo = factory.get_ebook_repository()
        regeneration_service = create_regeneration_service(factory)
        use_case = CompleteEbookPagesUseCase(
            ebook_repository=ebook_repo,
            regeneration_service=regeneration_service,
        )
        updated_ebook = await use_case.execute(ebook_id=ebook_id, target_pages=target_pages)
        return {
            "success": True,
            "message": f"Ebook completed to {updated_ebook.page_count} pages",
            "page_count": updated_ebook.page_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing ebook {ebook_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error completing ebook.") from e


@router.post("/{ebook_id}/add-pages")
async def add_pages(
    ebook_id: int,
    factory: RepositoryFactoryDep,
    body: Annotated[dict, Body(...)],
) -> dict:
    """Add new AI-generated pages to an existing ebook."""
    try:
        count = body.get("count", 1)
        if not isinstance(count, int) or count < 1:
            raise HTTPException(status_code=400, detail="count must be a positive integer")

        ebook_repo = factory.get_ebook_repository()
        page_service = create_page_service()
        regeneration_service = create_regeneration_service(factory)
        use_case = AddNewPagesUseCase(
            ebook_repository=ebook_repo,
            page_service=page_service,
            regeneration_service=regeneration_service,
        )
        result = await use_case.execute(ebook_id=ebook_id, count=count)
        return {
            "success": True,
            "message": result.message,
            "pages_added": result.pages_added,
            "total_pages": result.total_pages,
            "limit_reached": result.limit_reached,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding pages to ebook {ebook_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error adding pages.") from e
