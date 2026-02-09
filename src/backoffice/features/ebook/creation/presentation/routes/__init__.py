"""API routes for ebook creation feature."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response

from backoffice.features.ebook.creation.domain.entities.creation_request import CreationRequest
from backoffice.features.ebook.creation.domain.usecases.create_ebook import CreateEbookUseCase
from backoffice.features.ebook.listing.domain.usecases.get_ebooks import GetEbooksUseCase
from backoffice.features.ebook.shared.domain.entities.generation_request import (
    Audience,
    EbookType,
    GenerationRequest,
)
from backoffice.features.ebook.shared.domain.entities.pagination import PaginationParams
from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
    ThemeRepository,
)
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus
from backoffice.features.shared.presentation.routes.templates import templates

# Type alias for dependency injection
RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api/ebooks", tags=["Ebook Creation"])
logger = logging.getLogger(__name__)


@router.get("/form-config")
async def get_form_config() -> dict:
    """Get form configuration (themes and audiences) from YAML files.

    Returns:
        {
            "themes": [
                {"id": "dinosaurs", "label": "Dinosaures", "description": "..."},
                {"id": "unicorns", "label": "Licornes", "description": "..."},
                ...
            ],
            "audiences": [
                {"id": "children", "label": "Enfants", "complexity": "simple"},
                {"id": "adults", "label": "Adultes & Familles", "complexity": "detailed"}
            ]
        }
    """
    from pathlib import Path

    import yaml

    from backoffice.config import ConfigLoader

    config = ConfigLoader()

    # Load themes from config/branding/themes/ directory
    themes_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "config" / "branding" / "themes"
    themes = []

    for theme_file in sorted(themes_dir.glob("*.yml")):
        # Skip neutral-default (internal fallback)
        if theme_file.stem == "neutral-default":
            continue

        with open(theme_file, encoding="utf-8") as f:
            theme_data = yaml.safe_load(f)

        themes.append(
            {
                "id": theme_file.stem,
                "label": theme_data.get("label", theme_file.stem.capitalize()),
                "description": theme_data.get("description", ""),
            }
        )

    # Load audiences from config
    audiences_config = config.load_audiences()
    audiences = []

    for audience_id, audience_data in audiences_config["audiences"].items():
        audiences.append(
            {
                "id": audience_id,
                "label": audience_data["label"],
                "complexity": audience_data["style"]["complexity"],
                "benefits": audience_data.get("benefits", []),
            }
        )

    return {"themes": themes, "audiences": audiences}


@router.post("")
async def create_ebook(
    request: Request,
    factory: RepositoryFactoryDep,
    ebook_type: str = Form("coloring"),
    theme_id: str = Form(...),  # Required
    audience: str = Form(...),  # Required
    title: str = Form(None),
    author: str = Form("Assistant IA"),
    number_of_pages: int = Form(8),  # Default 8 pages
    preview_mode: bool = Form(False),  # Preview mode (1 page) vs Production (24 pages)
) -> Response:
    """Create a new coloring book ebook.

    This endpoint:
    1. Validates creation request parameters
    2. Generates ebook using strategy pattern
    3. Persists ebook to database
    4. Uploads to Google Drive (if available)
    5. Emits EbookCreatedEvent
    6. Returns updated ebooks list

    Args:
        request: FastAPI request object
        factory: Repository factory for dependency injection
        ebook_type: Type of ebook (only 'coloring' supported)
        theme_id: Theme identifier (e.g., 'dinosaur', 'pirate')
        audience: Target age group (e.g., '3-5', '6-8', '9-12')
        title: Optional title (auto-generated if not provided)
        author: Author name (defaults to 'Assistant IA')
        number_of_pages: Number of content pages (default 8)
        preview_mode: If True, generate only 1 page for preview

    Returns:
        HTML response with updated ebooks table

    Raises:
        ValueError: If validation fails or unsupported ebook type
    """
    logger.info(f"Creating coloring book - Theme: {theme_id}, Audience: {audience}")

    # Step 1: Validate request using CreationRequest value object
    creation_request = CreationRequest(
        ebook_type=ebook_type,
        theme_id=theme_id,
        audience=audience,
        title=title,
        author=author,
        number_of_pages=number_of_pages,
        preview_mode=preview_mode,
    )

    # Step 2: Load theme info
    theme_repository = ThemeRepository()
    logger.info(f"Loading theme with ID: {theme_id}")
    theme = theme_repository.get_theme_by_id(theme_id)

    # Step 3: Parse audience enum
    try:
        audience_enum = Audience(audience)
    except ValueError as err:
        raise ValueError(f"Invalid audience: '{audience}'. Must be 'children' or 'adults'. " f"Check config/branding/audiences.yaml") from err

    # Step 4: Determine page count based on mode
    # Preview mode: 1 page (+ cover + back cover = 3 images)
    # Production mode: use number_of_pages (default 24)
    is_preview = creation_request.preview_mode
    pages_count = 1 if is_preview else (creation_request.number_of_pages or 24)

    mode_label = "PREVIEW" if is_preview else "PRODUCTION"
    logger.info(f"🎨 Generating coloring book via UseCase + Strategy ({mode_label} MODE)")
    logger.info(f"   Theme: {theme.label} ({theme.blocks.subject})")
    logger.info(f"   Audience: {audience_enum.value}")
    logger.info(f"   Pages: {pages_count}")

    # Step 5: Create generation request
    request_id = str(uuid.uuid4())
    generation_request = GenerationRequest(
        title=creation_request.title or f"Coloring Book - {theme.label}",
        theme=theme_id,
        audience=audience_enum,
        ebook_type=EbookType.COLORING,
        page_count=pages_count,
        request_id=request_id,
        seed=None,
    )

    # Step 6: Create strategy and use case with dependencies
    from backoffice.features.ebook.creation.domain.strategies.strategy_factory import (
        StrategyFactory,
    )

    strategy = StrategyFactory.create_strategy(EbookType.COLORING)
    ebook_repo = factory.get_ebook_repository()
    file_storage = factory.get_file_storage()
    event_bus = EventBus()

    create_ebook_usecase = CreateEbookUseCase(
        ebook_repository=ebook_repo,
        generation_strategy=strategy,
        event_bus=event_bus,
        file_storage=file_storage,
    )

    # Step 7: Execute use case (emits EbookCreatedEvent)
    await create_ebook_usecase.execute(generation_request, is_preview=is_preview)

    # Step 8: Get updated ebooks list for response
    get_ebooks_usecase = GetEbooksUseCase(ebook_repo)
    pagination_params = PaginationParams(page=1, size=15)
    paginated_result = await get_ebooks_usecase.execute_paginated(pagination_params)

    ebooks_data = [
        {
            "id": e.id,
            "title": e.title,
            "author": e.author,
            "created_at": e.created_at,
            "status": e.status.value,
            "drive_id": e.drive_id,
        }
        for e in paginated_result.items
    ]

    pagination_data = {
        "current_page": paginated_result.page,
        "total_pages": paginated_result.total_pages,
        "total_count": paginated_result.total_count,
        "has_next": paginated_result.has_next,
        "has_previous": paginated_result.has_previous,
        "next_page": paginated_result.next_page,
        "previous_page": paginated_result.previous_page,
        "start_item": paginated_result.start_item,
        "end_item": paginated_result.end_item,
        "page_size": paginated_result.size,
    }

    response = templates.TemplateResponse(
        "partials/ebooks_table.html",
        {
            "request": request,
            "ebooks": ebooks_data,
            "pagination": pagination_data,
            "current_status": None,
        },
    )

    # Add HX-Trigger to close modal after creation
    response.headers["HX-Trigger"] = "ebookCreated"

    return response
