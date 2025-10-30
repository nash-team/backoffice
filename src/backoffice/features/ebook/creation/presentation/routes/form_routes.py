"""Form routes for ebook creation feature."""

import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, Request, Response

from backoffice.config import ConfigLoader
from backoffice.features.shared.presentation.routes.templates import templates

router = APIRouter(prefix="/api/dashboard", tags=["Ebook Creation Forms"])
logger = logging.getLogger(__name__)


@router.get("/ebooks/new")
async def get_new_ebook_form(request: Request) -> Response:
    """Display the new ebook creation form with themes and audiences from YAML."""
    logger.info("Loading enhanced ebook form with dynamic themes and audiences")

    config = ConfigLoader()

    # Load themes from config/branding/themes/ directory
    # From form_routes.py, go up 8 levels to reach project root, then into config/branding/themes
    themes_dir = (
        Path(__file__).parent.parent.parent.parent.parent.parent.parent.parent
        / "config"
        / "branding"
        / "themes"
    )
    logger.info(f"Loading themes from: {themes_dir}")
    logger.info(f"Themes directory exists: {themes_dir.exists()}")

    themes = []

    for theme_file in sorted(themes_dir.glob("*.yml")):
        # Skip neutral-default (internal fallback)
        if theme_file.stem == "neutral-default":
            logger.info(f"Skipping internal theme: {theme_file.stem}")
            continue

        logger.info(f"Loading theme: {theme_file.stem}")
        with open(theme_file, encoding="utf-8") as f:
            theme_data = yaml.safe_load(f)

        themes.append(
            {
                "id": theme_file.stem,
                "label": theme_data.get("label", theme_file.stem.capitalize()),
                "description": theme_data.get("description", ""),
            }
        )

    logger.info(f"Loaded {len(themes)} themes: {[t['id'] for t in themes]}")

    # Load audiences from config
    audiences_config = config.load_audiences()
    audiences = []

    for audience_id, audience_data in audiences_config["audiences"].items():
        complexity_label = (
            "Dessins simples et clairs"
            if audience_data["style"]["complexity"] == "simple"
            else "Dessins détaillés et complexes"
        )
        audiences.append(
            {
                "id": audience_id,
                "label": audience_data["label"],
                "complexity": complexity_label,
            }
        )

    return templates.TemplateResponse(
        "partials/enhanced_ebook_form.html",
        {"request": request, "themes": themes, "audiences": audiences},
    )
