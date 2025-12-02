"""API routes for ebook regeneration feature."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from backoffice.features.ebook.regeneration.domain.entities.page_type import PageType
from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.regeneration.domain.usecases.apply_page_edit import (
    ApplyPageEditUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.complete_ebook_pages import (
    CompleteEbookPagesUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.edit_page_image import (
    EditPageImageUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.preview_regenerate_page import (
    PreviewRegeneratePageUseCase,
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
        "page_indices": [1, 2, 3]  # Multiple pages (content_page only)
    }

    Returns:
        JSON response with success status and ebook details
    """
    try:
        # Extract and validate request parameters
        page_type_str = regeneration_request.get("page_type")
        page_index = regeneration_request.get("page_index")
        page_indices = regeneration_request.get("page_indices")

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


@router.post("/{ebook_id}/pages/{page_index}/preview-regenerate")
async def preview_regenerate_page(
    ebook_id: int,
    page_index: int,
    factory: RepositoryFactoryDep,
    body: dict | None = Body(default=None),
) -> dict:
    """Preview regenerate a content page without saving to DB or storage.

    This endpoint generates a new version of the page for preview purposes only.
    The image is returned as base64 but NOT saved to DB/storage.
    No PDF rebuild occurs.

    Args:
        ebook_id: ID of the ebook
        page_index: Index of the page to regenerate (1-based, content pages only)
        factory: Repository factory for dependency injection
        body: Optional request body that may include the current modal image

    Returns:
        JSON response with base64 image data and metadata

    Raises:
        HTTPException: If ebook not found, invalid status, or invalid page index
    """
    try:
        logger.info(f"Preview regenerating page {page_index} for ebook {ebook_id}")

        # Extract optional current modal image (for chaining)
        current_image_base64 = None
        if body:
            current_image_base64 = body.get("current_image_base64")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        page_provider = ProviderFactory.create_content_page_provider()
        page_service = ContentPageGenerationService(page_port=page_provider)

        # Create use case
        use_case = PreviewRegeneratePageUseCase(
            ebook_repository=ebook_repo,
            page_service=page_service,
        )

        # Execute preview regeneration
        result = await use_case.execute(
            ebook_id=ebook_id,
            page_index=page_index,
            current_image_base64=current_image_base64,
        )

        logger.info(f"✅ Preview regenerated page {page_index} for ebook {ebook_id}")

        return {
            "success": True,
            "image_base64": result["image_base64"],
            "page_index": result["page_index"],
            "prompt_used": result["prompt_used"],
        }

    except ValueError as e:
        logger.warning(f"Validation error preview regenerating page {page_index} for ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error preview regenerating page {page_index} for ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error preview regenerating page. Please try again.",
        ) from e


@router.post("/{ebook_id}/pages/{page_index}/edit")
async def edit_page_image(
    ebook_id: int,
    page_index: int,
    factory: RepositoryFactoryDep,
    edit_request: Annotated[dict, Body(...)],
) -> dict:
    """Edit a content page image with targeted corrections without saving to DB.

    This endpoint applies specific corrections to an existing page image.
    The edited image is returned as base64 but NOT saved to DB/storage.
    No PDF rebuild occurs - this is preview only.

    Request body:
    {
        "edit_prompt": "replace 5 toes with 3 toes",
        "current_image_base64": "<latest modal image, optional>"
    }

    Args:
        ebook_id: ID of the ebook
        page_index: Index of the page to edit (1-based, content pages only)
        factory: Repository factory for dependency injection
        edit_request: Request body with edit_prompt

    Returns:
        JSON response with base64 edited image data and metadata

    Raises:
        HTTPException: If ebook not found, invalid status, invalid page index, or edit fails
    """
    try:
        # Extract edit prompt and optional current image from request
        edit_prompt = edit_request.get("edit_prompt")
        if not edit_prompt:
            raise HTTPException(status_code=400, detail="edit_prompt is required in request body")
        current_image_base64 = edit_request.get("current_image_base64")

        logger.info(f"Editing page {page_index} for ebook {ebook_id} with prompt: {edit_prompt[:100]}...")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        image_edit_port = ProviderFactory.create_image_edit_provider()

        # Create use case
        use_case = EditPageImageUseCase(
            ebook_repository=ebook_repo,
            image_edit_port=image_edit_port,
        )

        # Execute edit
        result = await use_case.execute(
            ebook_id=ebook_id,
            page_index=page_index,
            edit_prompt=edit_prompt,
            current_image_base64=current_image_base64,
        )

        logger.info(f"✅ Edited page {page_index} for ebook {ebook_id}")

        return {
            "success": True,
            "image_base64": result["image_base64"],
            "page_index": result["page_index"],
            "edit_prompt_used": result["edit_prompt_used"],
        }

    except ValueError as e:
        logger.warning(f"Validation error editing page {page_index} for ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error editing page {page_index} for ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error editing page. Please try again.",
        ) from e


@router.post("/{ebook_id}/pages/{page_index}/apply-edit")
async def apply_page_edit(
    ebook_id: int,
    page_index: int,
    factory: RepositoryFactoryDep,
    edit_data: Annotated[dict, Body(...)],
) -> dict:
    """Apply a page edit by saving the preview image and rebuilding PDF.

    This endpoint:
    1. Receives base64 image from modal preview
    2. Updates ebook structure_json with new image
    3. Rebuilds PDF with new page
    4. Resets APPROVED ebook to DRAFT if necessary
    5. Saves to DB and storage

    Request body:
    {
        "image_base64": "base64-encoded-image-data",
        "page_index": 1
    }

    Args:
        ebook_id: ID of the ebook
        page_index: Index of the page to update (1-based, content pages only)
        factory: Repository factory for dependency injection
        edit_data: Request body with image_base64 and page_index

    Returns:
        JSON response with success status and updated ebook preview URL

    Raises:
        HTTPException: If ebook not found, invalid status, or save fails
    """
    try:
        logger.info(f"Applying edit for page {page_index} of ebook {ebook_id}")

        # Extract image data from request
        image_base64 = edit_data.get("image_base64")
        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 is required in request body")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        file_storage = factory.get_file_storage()
        event_bus = EventBus()

        # Create shared services for PDF reassembly
        assembly_provider = WeasyPrintAssemblyProvider()
        assembly_service = PDFAssemblyService(assembly_port=assembly_provider)
        regeneration_service = RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )

        # Create use case
        use_case = ApplyPageEditUseCase(
            ebook_repository=ebook_repo,
            regeneration_service=regeneration_service,
            event_bus=event_bus,
        )

        # Execute apply edit
        updated_ebook = await use_case.execute(
            ebook_id=ebook_id,
            page_index=page_index,
            image_base64=image_base64,
        )

        logger.info(f"✅ Successfully applied edit for page {page_index} of ebook {ebook_id}")

        return {
            "success": True,
            "message": f"Page {page_index} mise à jour avec succès",
            "ebook_id": updated_ebook.id,
            "preview_url": updated_ebook.preview_url,
        }

    except ValueError as e:
        logger.warning(f"Validation error applying edit for page {page_index} of ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error applying edit for page {page_index} of ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error applying edit. Please try again.",
        ) from e
