"""API routes for ebook export feature."""

import base64
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as FastAPIResponse

from backoffice.features.ebook.export.domain.usecases.export_ebook_pdf import ExportEbookPdfUseCase
from backoffice.features.ebook.export.domain.usecases.export_to_kdp import ExportToKDPUseCase
from backoffice.features.ebook.export.domain.usecases.export_to_kdp_interior import (
    ExportToKDPInteriorUseCase,
)
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils import (
    visual_validator,
)
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# Type alias for dependency injection
RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api/ebooks", tags=["Ebook Export"])
logger = logging.getLogger(__name__)


@router.get("/{ebook_id}/pdf")
async def export_ebook_pdf(ebook_id: int, factory: RepositoryFactoryDep) -> FastAPIResponse:
    """Export raw ebook PDF from database.

    This endpoint:
    1. Validates ebook exists
    2. Retrieves PDF bytes from database
    3. Emits EbookExportedEvent
    4. Returns PDF with proper headers for download

    Args:
        ebook_id: ID of the ebook to export
        factory: Repository factory for dependency injection

    Returns:
        PDF file response with inline disposition

    Raises:
        HTTPException: If ebook not found or PDF not available
    """
    try:
        logger.info(f"PDF export requested for ebook {ebook_id}")

        # Create use case with dependencies
        ebook_repo = factory.get_ebook_repository()
        event_bus = EventBus()
        use_case = ExportEbookPdfUseCase(ebook_repository=ebook_repo, event_bus=event_bus)

        # Execute export
        pdf_bytes = await use_case.execute(ebook_id)

        # Get ebook for filename
        ebook = await ebook_repo.get_by_id(ebook_id)
        filename = f"{ebook.title}.pdf" if ebook and ebook.title else f"ebook_{ebook_id}.pdf"

        # Return PDF with proper headers
        return FastAPIResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=3600",
            },
        )

    except DomainError as e:
        logger.warning(f"Domain error exporting PDF for ebook {ebook_id}: {e}")
        status_code = 404 if e.code.value == "EBOOK_NOT_FOUND" else 400
        raise HTTPException(status_code=status_code, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error serving PDF for ebook {ebook_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error serving PDF") from e


@router.get("/{ebook_id}/export-kdp")
async def export_ebook_to_kdp(
    ebook_id: int, factory: RepositoryFactoryDep, preview: bool = False
) -> FastAPIResponse:
    """Export ebook to Amazon KDP paperback format.

    This endpoint:
    1. Validates ebook status (APPROVED for download, DRAFT/APPROVED for preview)
    2. Assembles KDP PDF with bleed/trim specifications
    3. Emits KDPExportGeneratedEvent
    4. Returns PDF with proper headers

    Args:
        ebook_id: ID of the ebook to export
        factory: Repository factory for dependency injection
        preview: If True, display inline (allows DRAFT); if False, download (requires APPROVED)

    Returns:
        KDP-formatted PDF file response

    Raises:
        HTTPException: If ebook not found, invalid status, or export fails
    """
    try:
        logger.info(f"KDP export requested for ebook {ebook_id} (preview={preview})")

        # Create use case with dependencies
        ebook_repo = factory.get_ebook_repository()
        event_bus = EventBus()
        use_case = ExportToKDPUseCase(ebook_repository=ebook_repo, event_bus=event_bus)

        # Execute export (preview_mode=True allows DRAFT, False requires APPROVED)
        kdp_pdf_bytes = await use_case.execute(ebook_id, preview_mode=preview)

        # Get ebook for filename
        ebook = await ebook_repo.get_by_id(ebook_id)
        filename = (
            f"{ebook.title}_KDP.pdf" if ebook and ebook.title else f"ebook_{ebook_id}_KDP.pdf"
        )

        # Return PDF (inline for preview, attachment for download)
        disposition = "inline" if preview else "attachment"
        return FastAPIResponse(
            content=kdp_pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "Cache-Control": "no-cache",
            },
        )

    except DomainError as e:
        logger.warning(f"Domain error exporting ebook {ebook_id} to KDP: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotImplementedError as e:
        logger.warning(f"KDP export not yet implemented for ebook {ebook_id}")
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error exporting ebook {ebook_id} to KDP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error exporting to KDP") from e


@router.get("/{ebook_id}/export-kdp/interior")
async def export_ebook_to_kdp_interior(
    ebook_id: int, factory: RepositoryFactoryDep, preview: bool = False
) -> FastAPIResponse:
    """Export ebook interior/manuscript to Amazon KDP format.

    This endpoint:
    1. Validates ebook status (APPROVED for download, DRAFT/APPROVED for preview)
    2. Assembles KDP interior PDF with content pages only (no cover/back)
    3. Applies bleed/trim specifications for KDP
    4. Emits KDPExportGeneratedEvent
    5. Returns PDF with proper headers

    Args:
        ebook_id: ID of the ebook to export
        factory: Repository factory for dependency injection
        preview: If True, display inline (allows DRAFT); if False, download (requires APPROVED)

    Returns:
        KDP-formatted interior PDF file response

    Raises:
        HTTPException: If ebook not found, invalid status, or export fails
    """
    try:
        logger.info(f"KDP interior export requested for ebook {ebook_id} (preview={preview})")

        # Create use case with dependencies
        ebook_repo = factory.get_ebook_repository()
        event_bus = EventBus()
        use_case = ExportToKDPInteriorUseCase(ebook_repository=ebook_repo, event_bus=event_bus)

        # Execute export (preview_mode=True allows DRAFT, False requires APPROVED)
        kdp_interior_pdf_bytes = await use_case.execute(ebook_id, preview_mode=preview)

        # Get ebook for filename
        ebook = await ebook_repo.get_by_id(ebook_id)
        filename = (
            f"{ebook.title}_KDP_Interior.pdf"
            if ebook and ebook.title
            else f"ebook_{ebook_id}_KDP_Interior.pdf"
        )

        # Return PDF (inline for preview, attachment for download)
        disposition = "inline" if preview else "attachment"
        return FastAPIResponse(
            content=kdp_interior_pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "Cache-Control": "no-cache",
            },
        )

    except DomainError as e:
        logger.warning(f"Domain error exporting ebook {ebook_id} interior to KDP: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotImplementedError as e:
        logger.warning(f"KDP interior export not yet implemented for ebook {ebook_id}")
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error exporting ebook {ebook_id} interior to KDP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error exporting interior to KDP") from e


@router.get("/{ebook_id}/kdp-cover-preview")
async def get_kdp_cover_preview(ebook_id: int, factory: RepositoryFactoryDep) -> FastAPIResponse:
    """Get full KDP cover (back + spine + front) with KDP template overlay for visual validation.

    This endpoint:
    1. Retrieves ebook and validates it exists
    2. Extracts cover and back cover images
    3. Assembles full KDP cover (back + spine + front)
    4. Overlays official KDP template for visual validation
    5. Returns PNG image with overlay

    Args:
        ebook_id: ID of the ebook
        factory: Repository factory for dependency injection

    Returns:
        PNG image with KDP template overlay for visual validation

    Raises:
        HTTPException: If ebook not found or images not available
    """
    try:
        logger.info(f"KDP cover preview requested for ebook {ebook_id}")

        # Get ebook
        ebook_repo = factory.get_ebook_repository()
        ebook = await ebook_repo.get_by_id(ebook_id)

        if not ebook:
            raise HTTPException(status_code=404, detail=f"Ebook {ebook_id} not found")

        # Validate structure exists
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise HTTPException(
                status_code=400, detail="Ebook structure not available - no pages found"
            )

        # Extract cover and back cover from structure
        pages_meta = ebook.structure_json["pages_meta"]
        if not isinstance(pages_meta, list):
            raise HTTPException(status_code=400, detail="Invalid structure format")

        # Get cover (first page) and back cover (last page) by index, not by page_number
        # Note: page_number can be inconsistent after regeneration
        if len(pages_meta) < 2:
            raise HTTPException(
                status_code=400, detail="Ebook must have at least cover and back cover"
            )

        cover_page = pages_meta[0]  # First page
        back_cover_page = pages_meta[-1]  # Last page

        if not cover_page or not cover_page.get("image_data_base64"):
            raise HTTPException(status_code=400, detail="Cover image not available")

        if not back_cover_page or not back_cover_page.get("image_data_base64"):
            raise HTTPException(status_code=400, detail="Back cover image not available")

        # Decode base64 image data
        cover_bytes = base64.b64decode(cover_page["image_data_base64"])
        back_cover_bytes = base64.b64decode(back_cover_page["image_data_base64"])

        # Resize images to KDP required dimensions (8.5" × 8.5" @ 300 DPI = 2550×2550px)
        from io import BytesIO

        from PIL import Image

        # Resize cover
        cover_img = Image.open(BytesIO(cover_bytes))
        if cover_img.size != (2550, 2550):
            logger.info(f"Resizing cover from {cover_img.size} to (2550, 2550)")
            cover_img = cover_img.resize((2550, 2550), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            cover_img.save(buffer, format="PNG")
            cover_bytes = buffer.getvalue()

        # Resize back cover (barcode space is already present and will be resized proportionally)
        back_cover_img = Image.open(BytesIO(back_cover_bytes))
        if back_cover_img.size != (2550, 2550):
            logger.info(f"Resizing back cover from {back_cover_img.size} to (2550, 2550)")
            back_cover_img = back_cover_img.resize((2550, 2550), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            back_cover_img.save(buffer, format="PNG")
            back_cover_bytes = buffer.getvalue()

        # Assemble full KDP cover (back + spine + front)
        page_count = (
            ebook.config.number_of_pages if ebook.config and ebook.config.number_of_pages else 24
        )
        logger.warning(
            f"🔍 DEBUG: About to call assemble_full_kdp_cover() with page_count={page_count}"
        )
        logger.warning(f"   Back cover size: {len(back_cover_bytes)} bytes")
        logger.warning(f"   Front cover size: {len(cover_bytes)} bytes")

        try:
            full_cover_bytes = visual_validator.assemble_full_kdp_cover(
                back_cover_bytes=back_cover_bytes,
                front_cover_bytes=cover_bytes,
                page_count=page_count,
            )
            logger.warning(
                f"✅ DEBUG: assemble_full_kdp_cover() returned {len(full_cover_bytes)} bytes"
            )
        except Exception as e:
            logger.error(f"❌ EXCEPTION in assemble_full_kdp_cover(): {e}", exc_info=True)
            # Re-raise to see full traceback
            raise

        # Overlay KDP template for visual validation
        preview_bytes = visual_validator.overlay_kdp_template(
            full_cover_bytes, template_opacity=0.3, show_measurements=True
        )

        logger.info(f"✅ KDP cover preview generated for ebook {ebook_id}")

        # Return PNG image
        return FastAPIResponse(
            content=preview_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f'inline; filename="ebook_{ebook_id}_kdp_cover_preview.png"',
                "Cache-Control": "no-cache",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating KDP cover preview for ebook {ebook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error generating KDP cover preview: {str(e)}"
        ) from e
