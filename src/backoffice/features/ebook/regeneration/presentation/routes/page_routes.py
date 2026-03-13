"""API routes for page regeneration and editing."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from backoffice.features.ebook.regeneration.domain.usecases.apply_page_edit import (
    ApplyPageEditUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.edit_page_image import (
    EditPageImageUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.preview_regenerate_page import (
    PreviewRegeneratePageUseCase,
)
from backoffice.features.ebook.regeneration.presentation.routes.dependencies import (
    create_page_service,
    create_regeneration_service,
)
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.ebook.shared.infrastructure.providers.provider_factory import (
    ProviderFactory,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# Type alias for dependency injection
RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(tags=["Page Regeneration"])
logger = logging.getLogger(__name__)


@router.post("/{ebook_id}/pages/{page_index}/preview-regenerate")
async def preview_regenerate_page(
    ebook_id: int,
    page_index: int,
    factory: RepositoryFactoryDep,
    body: Annotated[dict | None, Body()] = None,
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

        # Extract optional parameters from body
        current_image_base64 = None
        custom_prompt = None
        if body:
            current_image_base64 = body.get("current_image_base64")
            custom_prompt = body.get("custom_prompt")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        page_service = create_page_service()

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
            custom_prompt=custom_prompt,
        )

        logger.info(f"Preview regenerated page {page_index} for ebook {ebook_id}")

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

        logger.info(f"Edited page {page_index} for ebook {ebook_id}")

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
    2. Updates ebook structure_json with new image and optional prompt
    3. Rebuilds PDF with new page
    4. Resets APPROVED ebook to DRAFT if necessary
    5. Saves to DB and storage

    Request body:
    {
        "image_base64": "base64-encoded-image-data",
        "page_index": 1,
        "prompt": "optional custom prompt used for regeneration"
    }

    Args:
        ebook_id: ID of the ebook
        page_index: Index of the page to update (0 for cover, 1+ for content pages)
        factory: Repository factory for dependency injection
        edit_data: Request body with image_base64, page_index, and optional prompt

    Returns:
        JSON response with success status and updated ebook preview URL

    Raises:
        HTTPException: If ebook not found, invalid status, or save fails
    """
    try:
        logger.info(f"Applying edit for page {page_index} of ebook {ebook_id}")

        # Extract image data and optional prompt from request
        image_base64 = edit_data.get("image_base64")
        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 is required in request body")
        prompt = edit_data.get("prompt")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        event_bus = EventBus()
        regeneration_service = create_regeneration_service(factory)

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
            prompt=prompt,
        )

        page_type = "Couverture" if page_index == 0 else f"Page {page_index}"
        logger.info(f"Successfully applied edit for {page_type} of ebook {ebook_id}")

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


@router.get("/{ebook_id}/pages/{page_index}/data")
async def get_page_data(
    ebook_id: int,
    page_index: int,
    factory: RepositoryFactoryDep,
) -> dict:
    """Get page data (image base64 + prompt) for editing.

    This endpoint returns the current image and prompt for a specific page,
    allowing the frontend to fetch data on-demand rather than embedding
    all images in the HTML.

    Args:
        ebook_id: ID of the ebook
        page_index: Index of the page (0 for cover, 1+ for content pages)
        factory: Repository factory for dependency injection

    Returns:
        JSON with image_base64 and prompt

    Raises:
        HTTPException: If ebook not found or invalid page index
    """
    try:
        ebook_repo = factory.get_ebook_repository()
        ebook = await ebook_repo.get_by_id(ebook_id)

        if not ebook:
            raise HTTPException(status_code=404, detail=f"Ebook {ebook_id} not found")

        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise HTTPException(status_code=400, detail="Ebook has no structure data")

        pages_meta = ebook.structure_json["pages_meta"]

        if page_index < 0 or page_index >= len(pages_meta):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid page index {page_index}. Must be between 0 and {len(pages_meta) - 1}",
            )

        page = pages_meta[page_index]
        return {
            "success": True,
            "ebook_id": ebook_id,
            "page_index": page_index,
            "image_base64": page.get("image_data_base64", ""),
            "prompt": page.get("prompt", ""),
            "title": page.get("title", f"Page {page_index}"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page data for ebook {ebook_id}, page {page_index}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving page data") from e
