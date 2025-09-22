import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backoffice.domain.entities.ebook_theme import (
    PREDEFINED_THEMES,
    EbookType,
    ExtendedEbookConfig,
    get_compatible_themes,
    get_theme_by_name,
)
from backoffice.infrastructure.adapters.modular_pdf_generator_adapter import (
    ModularPDFGeneratorAdapter,
)
from backoffice.presentation.routes.templates import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/themes", tags=["themes"])


class ThemeResponse(BaseModel):
    """Réponse contenant les informations d'un thème"""

    name: str
    display_name: str
    description: str
    cover_template: str
    toc_template: str
    text_template: str
    image_template: str
    compatible_types: list[str]


class AvailableTemplatesResponse(BaseModel):
    """Réponse contenant tous les templates disponibles par catégorie"""

    cover: list[str]
    toc: list[str]
    text: list[str]
    full_page_image: list[str]
    chapter_break: list[str]
    back_cover: list[str]


class CustomEbookRequest(BaseModel):
    """Requête pour générer un ebook avec configuration personnalisée"""

    title: str
    author: str
    ebook_type: str
    theme_name: str | None = None

    # Overrides de templates
    cover_template: str | None = None
    toc_template: str | None = None
    text_template: str | None = None
    image_template: str | None = None

    # Configuration standard
    cover_enabled: bool = True
    toc: bool = True
    format: str = "pdf"

    # Contenu
    story_chapters: list[dict] | None = None
    coloring_images: list[dict] | None = None


@router.get("/")
async def list_all_themes() -> list[ThemeResponse]:
    """Récupère la liste de tous les thèmes disponibles"""
    try:
        themes = []
        for theme in PREDEFINED_THEMES.values():
            themes.append(ThemeResponse(**theme.to_dict()))

        logger.info(f"Retour de {len(themes)} thèmes disponibles")
        return themes

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des thèmes: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur") from e


@router.get("/by-type/{ebook_type}/html")
async def get_themes_by_type_html(request: Request, ebook_type: str) -> HTMLResponse:
    """Récupère les thèmes compatibles avec un type d'ebook au format HTML"""
    try:
        # Valider le type d'ebook
        try:
            parsed_type = EbookType(ebook_type)
        except ValueError:
            return HTMLResponse(
                content='<div class="alert alert-danger">Type d\'ebook invalide</div>',
                status_code=400,
            )

        # Récupérer les thèmes compatibles
        compatible_themes = get_compatible_themes(parsed_type)
        themes_data = [theme.to_dict() for theme in compatible_themes]

        logger.info(f"Retour de {len(themes_data)} thèmes HTML pour {ebook_type}")

        template_response = templates.TemplateResponse(
            "partials/themes_selection.html", {"request": request, "themes": themes_data}
        )
        body = template_response.body
        content = body.decode() if isinstance(body, bytes) else bytes(body).decode()
        return HTMLResponse(content=content, status_code=200)

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des thèmes HTML: {e}")
        return HTMLResponse(
            content='<div class="alert alert-danger">Erreur lors du chargement des thèmes</div>',
            status_code=500,
        )


@router.get("/by-type/{ebook_type}")
async def get_themes_by_type(ebook_type: str) -> list[ThemeResponse]:
    """Récupère les thèmes compatibles avec un type d'ebook donné"""
    try:
        # Valider le type d'ebook
        try:
            parsed_type = EbookType(ebook_type)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Type d'ebook invalide: {ebook_type}. "
                f"Types supportés: {[t.value for t in EbookType]}",
            ) from e

        # Récupérer les thèmes compatibles
        compatible_themes = get_compatible_themes(parsed_type)
        themes = [ThemeResponse(**theme.to_dict()) for theme in compatible_themes]

        logger.info(f"Retour de {len(themes)} thèmes compatibles avec {ebook_type}")
        return themes

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des thèmes par type: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur") from e


@router.get("/{theme_name}")
async def get_theme_details(theme_name: str) -> ThemeResponse:
    """Récupère les détails d'un thème spécifique"""
    try:
        theme = get_theme_by_name(theme_name)
        if not theme:
            raise HTTPException(status_code=404, detail=f"Thème '{theme_name}' non trouvé")

        return ThemeResponse(**theme.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du thème {theme_name}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur") from e


@router.get("/templates/available")
async def get_available_templates() -> AvailableTemplatesResponse:
    """Récupère tous les templates disponibles par catégorie"""
    try:
        # Utiliser l'adaptateur modulaire pour récupérer les templates
        adapter = ModularPDFGeneratorAdapter()
        available_templates = adapter.get_available_templates()

        response = AvailableTemplatesResponse(
            cover=available_templates.get("cover", []),
            toc=available_templates.get("toc", []),
            text=available_templates.get("text", []),
            full_page_image=available_templates.get("full_page_image", []),
            chapter_break=available_templates.get("chapter_break", []),
            back_cover=available_templates.get("back_cover", []),
        )

        logger.info("Templates disponibles récupérés avec succès")
        return response

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des templates: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur") from e


@router.get("/types/available")
async def get_available_ebook_types() -> list[dict[str, str]]:
    """Récupère la liste des types d'ebooks disponibles"""
    try:
        types = []
        for ebook_type in EbookType:
            types.append(
                {
                    "value": ebook_type.value,
                    "label": _get_type_display_name(ebook_type),
                    "description": _get_type_description(ebook_type),
                }
            )

        logger.info(f"Retour de {len(types)} types d'ebooks disponibles")
        return types

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des types d'ebooks: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur") from e


@router.post("/preview")
async def generate_ebook_with_theme(request: CustomEbookRequest) -> dict[str, Any]:
    """Génère un ebook avec un thème personnalisé (pour preview)"""
    try:
        # Valider le type d'ebook
        try:
            ebook_type = EbookType(request.ebook_type)
        except ValueError as e:
            raise HTTPException(
                status_code=400, detail=f"Type d'ebook invalide: {request.ebook_type}"
            ) from e

        # Créer la configuration étendue
        config = ExtendedEbookConfig(
            ebook_type=ebook_type,
            theme_name=request.theme_name,
            cover_template=request.cover_template,
            toc_template=request.toc_template,
            text_template=request.text_template,
            image_template=request.image_template,
            cover_enabled=request.cover_enabled,
            toc=request.toc,
            format=request.format,
        )

        # Récupérer le thème si spécifié
        theme = None
        if request.theme_name:
            theme = get_theme_by_name(request.theme_name)
            if not theme:
                raise HTTPException(
                    status_code=400, detail=f"Thème '{request.theme_name}' non trouvé"
                )

        # Récupérer les templates effectifs
        effective_templates = config.get_effective_templates(theme)

        logger.info(f"Génération ebook preview avec thème: {request.theme_name}")
        logger.debug(f"Templates effectifs: {effective_templates}")

        # Pour l'instant, retourner juste la configuration
        # L'implémentation complète de génération sera ajoutée plus tard
        return {
            "status": "preview_ready",
            "config": {
                "title": request.title,
                "author": request.author,
                "ebook_type": ebook_type.value,
                "theme_name": request.theme_name,
                "effective_templates": effective_templates,
            },
            "message": "Configuration validée avec succès",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la génération preview: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur") from e


def _get_type_display_name(ebook_type: EbookType) -> str:
    """Récupère le nom d'affichage d'un type d'ebook"""
    match ebook_type:
        case EbookType.STORY:
            return "Histoire"
        case EbookType.COLORING:
            return "Livre de Coloriage"
        case EbookType.MIXED:
            return "Mixte (Histoire + Coloriage)"
        case _:
            return "Autre"


def _get_type_description(ebook_type: EbookType) -> str:
    """Récupère la description d'un type d'ebook"""
    match ebook_type:
        case EbookType.STORY:
            return "Livre d'histoire classique avec chapitres et narration"
        case EbookType.COLORING:
            return "Livre de coloriage avec images à colorier"
        case EbookType.MIXED:
            return "Combinaison d'histoire et de pages de coloriage"
        case _:
            return "Type d'ebook personnalisé"
