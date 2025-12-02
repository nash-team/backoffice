"""Helper for loading workflow parameters and building prompts from theme YAML."""

import logging
from pathlib import Path
from typing import Literal

import yaml

logger = logging.getLogger(__name__)


def load_workflow_params(theme_id: str, image_type: str, themes_directory: Path) -> dict[str, str]:
    """Load workflow_params from theme YAML based on configured provider.

    Args:
        theme_id: Theme identifier
        image_type: Type of image ("cover" or "coloring_page")
        themes_directory: Path to themes directory

    Returns:
        Dictionary of workflow parameters (node_id -> value)
    """
    from backoffice.config.loader import get_config_loader

    # Get template key based on provider configuration
    config = get_config_loader()
    template_key = config.get_template_key_for_type(image_type)

    logger.info(f"Loading workflow_params for {image_type} using template: {template_key}")

    # Load theme YAML
    theme_file = themes_directory / f"{theme_id}.yml"
    if not theme_file.exists():
        logger.warning(f"Theme file not found: {theme_file}, returning empty workflow_params")
        return {}

    with theme_file.open("r", encoding="utf-8") as f:
        theme_data = yaml.safe_load(f)

    # Get the appropriate template section
    if image_type == "cover":
        templates = theme_data.get("cover_templates", {})
    else:
        templates = theme_data.get("coloring_page_templates", {})

    template = templates.get(template_key, {})
    workflow_params_raw = template.get("workflow_params", {})

    # Ensure all values are strings
    workflow_params: dict[str, str] = {}
    for key, value in workflow_params_raw.items():
        workflow_params[str(key)] = str(value)

    logger.debug(f"Loaded workflow_params: {workflow_params}")
    return workflow_params


def build_cover_prompt_from_yaml(theme_id: str, themes_directory: Path) -> str:
    """Build cover prompt from theme YAML template.

    Args:
        theme_id: Theme identifier
        themes_directory: Path to themes directory

    Returns:
        Cover prompt string
    """
    from backoffice.config.loader import get_config_loader

    config = get_config_loader()
    template_key = config.get_template_key_for_type("cover")

    # Load theme YAML
    theme_file = themes_directory / f"{theme_id}.yml"
    with theme_file.open("r", encoding="utf-8") as f:
        theme_data = yaml.safe_load(f)

    cover_template = theme_data.get("cover_templates", {}).get(template_key, {})

    # Check if we have a direct prompt (comfy style) or prompt_blocks (default style)
    base_prompt: str
    if "prompt" in cover_template:
        # ComfyUI style: direct prompt
        base_prompt = str(cover_template["prompt"])
    elif "prompt_blocks" in cover_template:
        # Default style: build from blocks
        blocks = cover_template["prompt_blocks"]
        parts = []
        for key in ["main_subject", "setting", "style", "quality_tags"]:
            if key in blocks:
                parts.append(str(blocks[key]))
        base_prompt = ", ".join(parts)
    else:
        # Fallback
        base_prompt = f"{theme_id} themed children's book cover"

    return base_prompt


def build_page_prompt_from_yaml(
    theme_id: str,
    page_index: int,
    total_pages: int,
    themes_directory: Path,
    seed: int,
    audience: Literal["children", "adults"] | None = "children",
) -> str:
    """Build content page prompt from theme YAML template.

    Args:
        theme_id: Theme identifier
        page_index: Page index (0-based)
        total_pages: Total number of pages
        themes_directory: Path to themes directory
        seed: Random seed for reproducibility
        audience: Target audience ("children" or "adults")

    Returns:
        Content page prompt string
    """
    from backoffice.config.loader import get_config_loader
    from backoffice.features.ebook.shared.domain.services.prompt_template_engine import (
        PromptTemplateEngine,
    )

    config = get_config_loader()
    template_key = config.get_template_key_for_type("coloring_page")

    engine = PromptTemplateEngine(seed=seed)

    # Normalize audience and generate single prompt using the engine
    audience_normalized = audience or "children"
    prompts = engine.generate_prompts(
        theme=theme_id,
        count=total_pages,
        audience=audience_normalized,
        template_key=template_key,
    )

    # Return the prompt for this specific page index
    if page_index < len(prompts):
        return prompts[page_index]

    # Fallback
    return f"{theme_id} themed coloring page {page_index + 1}"
