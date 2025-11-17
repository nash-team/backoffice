"""API routes for ebook regeneration feature."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from backoffice.features.ebook.regeneration.domain.entities.page_type import PageType
from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.regeneration.domain.usecases.complete_ebook_pages import (
    CompleteEbookPagesUseCase,
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
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.ebook.shared.infrastructure.providers.provider_factory import (
    ProviderFactory,
)
from backoffice.features.ebook.shared.infrastructure.providers.weasyprint_assembly_provider import (
    WeasyPrintAssemblyProvider,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# Type alias for dependency injection
RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api/ebooks", tags=["Ebook Regeneration"])
logger = logging.getLogger(__name__)


@router.post("/{ebook_id}/pages/regenerate")
async def regenerate_ebook_page(
    ebook_id: int,
    request: Request,
    factory: RepositoryFactoryDep,
    regeneration_request: Annotated[dict, Body(...)],
) -> dict:
    """Regenerate one or more pages of an ebook.

    Request body:
    {
        "page_type": "cover" | "back_cover" | "content_page",
        "page_index": 0,  # Single page (for backward compatibility)
        "page_indices": [1, 2, 3],  # Multiple pages (content_page only)
        "prompt_override": "optional custom prompt"
    }

    Returns:
        JSON response with success status and ebook details
    """
    try:
        # Extract and validate request parameters
        page_type_str = regeneration_request.get("page_type")
        page_index = regeneration_request.get("page_index")
        page_indices = regeneration_request.get("page_indices")
        prompt_override = regeneration_request.get("prompt_override")

        if not page_type_str:
            raise HTTPException(status_code=400, detail="page_type is required")

        # Validate page_type
        try:
            page_type = PageType(page_type_str)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=(f"Invalid page_type. Must be one of: cover, back_cover, content_page. " f"Got: {page_type_str}"),
            ) from e

        # Get dependencies from factory
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()
        event_bus = EventBus()

        # Create shared services
        assembly_provider = WeasyPrintAssemblyProvider()
        assembly_service = PDFAssemblyService(assembly_port=assembly_provider)
        regeneration_service = RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )

        # Choose the appropriate use case based on page_type
        regenerate_usecase: RegenerateCoverUseCase | RegenerateBackCoverUseCase | RegenerateContentPageUseCase

        if page_type == PageType.COVER:
            logger.info(f"Regenerating cover for ebook {ebook_id}")
            cover_provider = ProviderFactory.create_cover_provider()
            cover_service = CoverGenerationService(cover_port=cover_provider)

            regenerate_usecase = RegenerateCoverUseCase(
                ebook_repository=ebook_repo,
                cover_service=cover_service,
                regeneration_service=regeneration_service,
                event_bus=event_bus,
            )
            updated_ebook = await regenerate_usecase.execute(
                ebook_id=ebook_id,
                prompt_override=prompt_override,
            )

        elif page_type == PageType.BACK_COVER:
            logger.info(f"Regenerating back_cover for ebook {ebook_id}")
            cover_provider = ProviderFactory.create_cover_provider()
            cover_service = CoverGenerationService(cover_port=cover_provider)

            regenerate_usecase = RegenerateBackCoverUseCase(
                ebook_repository=ebook_repo,
                cover_service=cover_service,
                regeneration_service=regeneration_service,
                event_bus=event_bus,
            )
            updated_ebook = await regenerate_usecase.execute(
                ebook_id=ebook_id,
                prompt_override=prompt_override,
            )

        else:  # PageType.CONTENT_PAGE
            page_provider = ProviderFactory.create_content_page_provider()
            page_service = ContentPageGenerationService(page_port=page_provider)

            regenerate_usecase = RegenerateContentPageUseCase(
                ebook_repository=ebook_repo,
                page_service=page_service,
                regeneration_service=regeneration_service,
                event_bus=event_bus,
            )

            # Handle multiple pages or single page
            if page_indices and isinstance(page_indices, list) and len(page_indices) > 0:
                # Multiple pages regeneration
                logger.info(f"Regenerating {len(page_indices)} pages for ebook {ebook_id}: {page_indices}")

                # Regenerate each page sequentially
                for idx in page_indices:
                    logger.info(f"Regenerating page {idx}...")
                    updated_ebook = await regenerate_usecase.execute(
                        ebook_id=ebook_id,
                        page_index=idx,
                        prompt_override=prompt_override,
                    )

                message = f"{len(page_indices)} pages regenerated successfully"
            else:
                # Single page regeneration (backward compatibility)
                if page_index is None:
                    raise HTTPException(
                        status_code=400,
                        detail=("Either page_index or page_indices must be provided " "for content_page"),
                    )

                logger.info(f"Regenerating page {page_index} for ebook {ebook_id}")
                updated_ebook = await regenerate_usecase.execute(
                    ebook_id=ebook_id,
                    page_index=page_index,
                    prompt_override=prompt_override,
                )
                message = f"Page {page_index} regenerated successfully"

        if page_type != PageType.CONTENT_PAGE:
            message = f"{page_type.value} regenerated successfully"

        logger.info(f"Successfully regenerated for ebook {ebook_id}")

        return {
            "success": True,
            "message": message,
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


@router.post("/{ebook_id}/complete-pages")
async def complete_ebook_pages(
    ebook_id: int,
    factory: RepositoryFactoryDep,
    target_pages: int = 24,
) -> dict:
    """Complete ebook with blank pages to reach KDP minimum (24 pages).

    This endpoint is useful for testing KDP exports without generating full ebooks.
    It adds white blank pages between the last content page and the back cover.

    Args:
        ebook_id: ID of the ebook to complete
        factory: Repository factory for dependency injection
        target_pages: Target page count (default: 24 for KDP minimum)

    Returns:
        JSON response with success message and new page count

    Raises:
        HTTPException: If ebook not found or error occurs
    """
    try:
        logger.info(f"Completing ebook {ebook_id} to {target_pages} pages")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()

        # Create shared services for PDF reassembly
        assembly_provider = WeasyPrintAssemblyProvider()
        assembly_service = PDFAssemblyService(assembly_port=assembly_provider)
        regeneration_service = RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )

        # Create use case with regeneration service
        use_case = CompleteEbookPagesUseCase(
            ebook_repository=ebook_repo,
            regeneration_service=regeneration_service,
        )

        updated_ebook = await use_case.execute(ebook_id=ebook_id, target_pages=target_pages)

        logger.info(f"✅ Ebook {ebook_id} completed to {updated_ebook.page_count} pages")

        return {
            "success": True,
            "message": f"Ebook completed to {updated_ebook.page_count} pages",
            "page_count": updated_ebook.page_count,
        }

    except ValueError as e:
        logger.warning(f"Validation error completing ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error completing ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error completing ebook. Please try again.",
        ) from e
