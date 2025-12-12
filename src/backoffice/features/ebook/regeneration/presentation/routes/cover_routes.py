"""API routes for cover regeneration and editing."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from backoffice.features.ebook.regeneration.domain.usecases.apply_page_edit import (
    ApplyPageEditUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.edit_cover_image import (
    EditCoverImageUseCase,
)
from backoffice.features.ebook.regeneration.domain.usecases.preview_regenerate_cover import (
    PreviewRegenerateCoverUseCase,
)
from backoffice.features.ebook.regeneration.presentation.routes.dependencies import (
    create_cover_service,
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

router = APIRouter(tags=["Cover Regeneration"])
logger = logging.getLogger(__name__)


@router.post("/{ebook_id}/cover/preview-regenerate")
async def preview_regenerate_cover(
    ebook_id: int,
    factory: RepositoryFactoryDep,
    body: Annotated[dict | None, Body()] = None,
) -> dict:
    """Preview regenerate the cover without saving to DB or storage.

    This endpoint generates a new version of the cover for preview purposes only.
    The image is returned as base64 but NOT saved to DB/storage.
    No PDF rebuild occurs.

    Request body (optional):
    {
        "current_image_base64": "<latest modal image for chaining>",
        "custom_prompt": "<custom prompt to use instead of stored/template>"
    }

    Args:
        ebook_id: ID of the ebook
        factory: Repository factory for dependency injection
        body: Optional request body with current_image_base64 and/or custom_prompt

    Returns:
        JSON response with base64 image data and metadata

    Raises:
        HTTPException: If ebook not found or invalid status
    """
    try:
        logger.info(f"Preview regenerating cover for ebook {ebook_id}")

        # Extract optional parameters from body
        current_image_base64 = None
        custom_prompt = None
        if body:
            current_image_base64 = body.get("current_image_base64")
            custom_prompt = body.get("custom_prompt")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        cover_service = create_cover_service()

        # Create use case
        use_case = PreviewRegenerateCoverUseCase(
            ebook_repository=ebook_repo,
            cover_service=cover_service,
        )

        # Execute preview regeneration
        result = await use_case.execute(
            ebook_id=ebook_id,
            current_image_base64=current_image_base64,
            custom_prompt=custom_prompt,
        )

        logger.info(f"Preview regenerated cover for ebook {ebook_id}")

        return {
            "success": True,
            "image_base64": result["image_base64"],
            "page_index": result["page_index"],
            "prompt_used": result["prompt_used"],
        }

    except ValueError as e:
        logger.warning(f"Validation error preview regenerating cover for ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error preview regenerating cover for ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error preview regenerating cover. Please try again.",
        ) from e


@router.post("/{ebook_id}/cover/edit")
async def edit_cover_image(
    ebook_id: int,
    factory: RepositoryFactoryDep,
    edit_request: Annotated[dict, Body(...)],
) -> dict:
    """Edit the cover image with targeted corrections without saving to DB.

    This endpoint applies specific corrections to an existing cover image.
    The edited image is returned as base64 but NOT saved to DB/storage.
    No PDF rebuild occurs - this is preview only.

    Request body:
    {
        "edit_prompt": "replace 5 toes with 3 toes",
        "current_image_base64": "<latest modal image, optional>"
    }

    Args:
        ebook_id: ID of the ebook
        factory: Repository factory for dependency injection
        edit_request: Request body with edit_prompt

    Returns:
        JSON response with base64 edited image data and metadata

    Raises:
        HTTPException: If ebook not found, invalid status, or edit fails
    """
    try:
        # Extract edit prompt and optional current image from request
        edit_prompt = edit_request.get("edit_prompt")
        if not edit_prompt:
            raise HTTPException(status_code=400, detail="edit_prompt is required in request body")
        current_image_base64 = edit_request.get("current_image_base64")

        logger.info(f"Editing cover for ebook {ebook_id} with prompt: {edit_prompt[:100]}...")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        image_edit_port = ProviderFactory.create_image_edit_provider()

        # Create use case
        use_case = EditCoverImageUseCase(
            ebook_repository=ebook_repo,
            image_edit_port=image_edit_port,
        )

        # Execute edit
        result = await use_case.execute(
            ebook_id=ebook_id,
            edit_prompt=edit_prompt,
            current_image_base64=current_image_base64,
        )

        logger.info(f"Edited cover for ebook {ebook_id}")

        return {
            "success": True,
            "image_base64": result["image_base64"],
            "page_index": result["page_index"],
            "edit_prompt_used": result["edit_prompt_used"],
        }

    except ValueError as e:
        logger.warning(f"Validation error editing cover for ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error editing cover for ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error editing cover. Please try again.",
        ) from e


@router.post("/{ebook_id}/cover/apply-edit")
async def apply_cover_edit(
    ebook_id: int,
    factory: RepositoryFactoryDep,
    edit_data: Annotated[dict, Body(...)],
) -> dict:
    """Apply a cover edit by saving the preview image and rebuilding PDF.

    This endpoint:
    1. Receives base64 image from modal preview
    2. Updates ebook structure_json with new cover image and optional prompt
    3. Rebuilds PDF with new cover
    4. Resets APPROVED ebook to DRAFT if necessary
    5. Saves to DB and storage

    Request body:
    {
        "image_base64": "base64-encoded-image-data",
        "prompt": "optional custom prompt used for regeneration"
    }

    Args:
        ebook_id: ID of the ebook
        factory: Repository factory for dependency injection
        edit_data: Request body with image_base64 and optional prompt

    Returns:
        JSON response with success status and updated ebook preview URL

    Raises:
        HTTPException: If ebook not found, invalid status, or save fails
    """
    try:
        logger.info(f"Applying edit for cover of ebook {ebook_id}")

        # Extract image data and optional prompt from request
        image_base64 = edit_data.get("image_base64")
        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 is required in request body")
        prompt = edit_data.get("prompt")

        # Get dependencies
        ebook_repo = factory.get_ebook_repository()
        event_bus = EventBus()
        regeneration_service = create_regeneration_service(factory)

        # Create use case (reuse ApplyPageEditUseCase with page_index=0)
        use_case = ApplyPageEditUseCase(
            ebook_repository=ebook_repo,
            regeneration_service=regeneration_service,
            event_bus=event_bus,
        )

        # Execute apply edit with page_index=0 for cover
        updated_ebook = await use_case.execute(
            ebook_id=ebook_id,
            page_index=0,  # Cover is always at index 0
            image_base64=image_base64,
            prompt=prompt,
        )

        logger.info(f"Successfully applied edit for cover of ebook {ebook_id}")

        return {
            "success": True,
            "message": "Couverture mise à jour avec succès",
            "ebook_id": updated_ebook.id,
            "preview_url": updated_ebook.preview_url,
        }

    except ValueError as e:
        logger.warning(f"Validation error applying edit for cover of ebook {ebook_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error applying edit for cover of ebook {ebook_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Error applying cover edit. Please try again.",
        ) from e
