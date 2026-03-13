"""JSON API routes for ebook creation (React SPA consumption)."""

import logging
import uuid
from pathlib import Path
from typing import Annotated

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backoffice.config import ConfigLoader
from backoffice.features.ebook.creation.domain.entities.creation_request import CreationRequest
from backoffice.features.ebook.creation.domain.usecases.create_ebook import CreateEbookUseCase
from backoffice.features.ebook.shared.domain.entities.generation_request import (
    Audience,
    EbookType,
    GenerationRequest,
)
from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
    ThemeRepository,
)
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
    get_repository_factory,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

RepositoryFactoryDep = Annotated[RepositoryFactory, Depends(get_repository_factory)]

router = APIRouter(prefix="/api", tags=["Ebook Creation API"])
logger = logging.getLogger(__name__)


@router.get("/ebooks/form-config")
async def get_form_config() -> dict:
    """Get form configuration (themes and audiences) from YAML files."""
    config = ConfigLoader()

    themes_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent.parent / "config" / "branding" / "themes"
    themes = []

    for theme_file in sorted(themes_dir.glob("*.yml")):
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

    audiences_config = config.load_audiences()
    audiences = [
        {
            "id": audience_id,
            "label": audience_data["label"],
            "complexity": audience_data["style"]["complexity"],
            "benefits": audience_data.get("benefits", []),
        }
        for audience_id, audience_data in audiences_config["audiences"].items()
    ]

    return {"themes": themes, "audiences": audiences}


class CreateEbookBody(BaseModel):
    title: str | None = None
    theme: str
    audience: str
    num_pages: int = 8
    preview_mode: bool = False


@router.post("/ebooks")
async def create_ebook_json(
    body: CreateEbookBody,
    factory: RepositoryFactoryDep,
) -> dict:
    """Create a new coloring book (JSON request/response)."""
    logger.info(f"[API] Creating coloring book - Theme: {body.theme}, Audience: {body.audience}")

    creation_request = CreationRequest(
        ebook_type="coloring",
        theme_id=body.theme,
        audience=body.audience,
        title=body.title,
        author="Assistant IA",
        number_of_pages=body.num_pages,
        preview_mode=body.preview_mode,
    )

    theme_repository = ThemeRepository()
    theme = theme_repository.get_theme_by_id(body.theme)

    try:
        audience_enum = Audience(body.audience)
    except ValueError as err:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audience: '{body.audience}'. Must be 'children' or 'adults'.",
        ) from err

    pages_count = 1 if creation_request.preview_mode else (creation_request.number_of_pages or 24)

    generation_request = GenerationRequest(
        title=creation_request.title or f"Coloring Book - {theme.label}",
        theme=body.theme,
        audience=audience_enum,
        ebook_type=EbookType.COLORING,
        page_count=pages_count,
        request_id=str(uuid.uuid4()),
        seed=None,
    )

    from backoffice.features.ebook.creation.domain.strategies.strategy_factory import (
        StrategyFactory,
    )

    strategy = StrategyFactory.create_strategy(EbookType.COLORING)
    ebook_repo = factory.get_ebook_repository()
    file_storage = factory.get_file_storage()
    event_bus = EventBus()

    use_case = CreateEbookUseCase(
        ebook_repository=ebook_repo,
        generation_strategy=strategy,
        event_bus=event_bus,
        file_storage=file_storage,
    )

    ebook = await use_case.execute(generation_request, is_preview=creation_request.preview_mode)

    return {
        "id": ebook.id,
        "title": ebook.title,
        "status": ebook.status.value,
        "num_pages": ebook.page_count,
        "created_at": ebook.created_at.isoformat() if ebook.created_at else None,
    }
