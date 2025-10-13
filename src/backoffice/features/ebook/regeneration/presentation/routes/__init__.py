"""API routes for ebook regeneration feature."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from backoffice.features.ebook.regeneration.domain.entities.page_type import PageType
from backoffice.features.ebook.regeneration.domain.entities.regeneration_request import (
    RegenerationRequest,
)
from backoffice.features.ebook.regeneration.domain.usecases.regenerate_back_cover import (
    RegenerateBackCoverUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.regenerate_content_page import (
    RegenerateContentPageUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.regenerate_cover import (
    RegenerateCoverUseCase,
)
from backoffice.features.ebook.shared.domain.services.cover_generation import CoverGenerationService
from backoffice.features.ebook.shared.domain.services.page_generation import (
    ContentPageGenerationService,
)
from backoffice.features.ebook.shared.domain.services.pdf_assembly import PDFAssemblyService
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    AsyncRepositoryFactory,
    get_async_repository_factory,
)
from backoffice.features.ebook.shared.infrastructure.providers.provider_factory import (
    ProviderFactory,
)
from backoffice.features.ebook.shared.infrastructure.providers.weasyprint_assembly_provider import (
    WeasyPrintAssemblyProvider,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# Type alias for dependency injection
AsyncRepositoryFactoryDep = Annotated[AsyncRepositoryFactory, Depends(get_async_repository_factory)]

router = APIRouter(prefix="/api/ebooks", tags=["Ebook Regeneration"])
logger = logging.getLogger(__name__)


@router.post("/{ebook_id}/pages/regenerate")
async def regenerate_ebook_page(
    ebook_id: int,
    request: Request,
    factory: AsyncRepositoryFactoryDep,
    regeneration_request: Annotated[dict, Body(...)],
) -> dict:
    """Regenerate a specific page of an ebook.

    Request body:
    {
        "page_type": "cover" | "back_cover" | "content_page",
        "page_index": 0,  # Only for content_page
        "prompt_override": "optional custom prompt"
    }

    Returns:
        JSON response with success status and ebook details
    """
    try:
        # Extract and validate request parameters
        page_type_str = regeneration_request.get("page_type")
        page_index = regeneration_request.get("page_index")
        prompt_override = regeneration_request.get("prompt_override")

        if not page_type_str:
            raise HTTPException(status_code=400, detail="page_type is required")

        # Validate page_type
        try:
            page_type = PageType(page_type_str)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid page_type. Must be one of: cover, back_cover, content_page. "
                    f"Got: {page_type_str}"
                ),
            ) from e

        # Create RegenerationRequest value object (with validation)
        try:
            regen_request = RegenerationRequest(
                ebook_id=ebook_id,
                page_type=page_type,
                page_index=page_index,
                prompt_override=prompt_override,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        logger.info(f"Regenerating {page_type.value} for ebook {ebook_id}")

        # Get dependencies from factory
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()
        event_bus = EventBus()

        # Setup event-driven cost tracking
        request_id = f"regenerate-{page_type.value}-{ebook_id}"
        track_usage_usecase = factory.get_track_token_usage_usecase()

        # Create services
        assembly_provider = WeasyPrintAssemblyProvider()
        assembly_service = PDFAssemblyService(assembly_port=assembly_provider)

        # Choose the appropriate use case based on page_type
        regenerate_usecase: (
            RegenerateCoverUseCase | RegenerateBackCoverUseCase | RegenerateContentPageUseCase
        )

        if page_type == PageType.COVER:
            cover_provider = ProviderFactory.create_cover_provider(
                track_usage_usecase=track_usage_usecase, request_id=request_id
            )
            cover_service = CoverGenerationService(cover_port=cover_provider)

            regenerate_usecase = RegenerateCoverUseCase(
                ebook_repository=ebook_repo,
                cover_service=cover_service,
                assembly_service=assembly_service,
                file_storage=file_storage,
                event_bus=event_bus,
            )
            updated_ebook = await regenerate_usecase.execute(
                ebook_id=ebook_id,
                prompt_override=prompt_override,
            )

        elif page_type == PageType.BACK_COVER:
            cover_provider = ProviderFactory.create_cover_provider(
                track_usage_usecase=track_usage_usecase, request_id=request_id
            )
            cover_service = CoverGenerationService(cover_port=cover_provider)

            regenerate_usecase = RegenerateBackCoverUseCase(
                ebook_repository=ebook_repo,
                cover_service=cover_service,
                assembly_service=assembly_service,
                file_storage=file_storage,
                event_bus=event_bus,
            )
            updated_ebook = await regenerate_usecase.execute(
                ebook_id=ebook_id,
                prompt_override=prompt_override,
            )

        else:  # PageType.CONTENT_PAGE
            page_provider = ProviderFactory.create_content_page_provider(
                track_usage_usecase=track_usage_usecase, request_id=request_id
            )
            page_service = ContentPageGenerationService(page_port=page_provider)

            regenerate_usecase = RegenerateContentPageUseCase(
                ebook_repository=ebook_repo,
                page_service=page_service,
                assembly_service=assembly_service,
                file_storage=file_storage,
                event_bus=event_bus,
            )
            updated_ebook = await regenerate_usecase.execute(
                ebook_id=ebook_id,
                page_index=regen_request.page_index,  # type: ignore
                prompt_override=prompt_override,
            )

        logger.info(f"Successfully regenerated {page_type.value} for ebook {ebook_id}")

        return {
            "success": True,
            "message": f"{page_type.value} regenerated successfully",
            "ebook_id": updated_ebook.id,
            "preview_url": updated_ebook.preview_url,
        }

    except ValueError as e:
        logger.warning(f"Validation error regenerating page for ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error regenerating page for ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error regenerating page. Please try again.",
        ) from e
