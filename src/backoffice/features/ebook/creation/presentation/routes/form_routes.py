"""Form routes for ebook creation feature."""

import logging

from fastapi import APIRouter, Request, Response

from backoffice.features.shared.presentation.routes.templates import templates

router = APIRouter(prefix="/api/dashboard", tags=["Ebook Creation Forms"])
logger = logging.getLogger(__name__)


@router.get("/ebooks/new")
async def get_new_ebook_form(request: Request) -> Response:
    """Display the new ebook creation form with theme selection."""
    logger.info("Loading enhanced ebook form")
    return templates.TemplateResponse("partials/enhanced_ebook_form.html", {"request": request})
