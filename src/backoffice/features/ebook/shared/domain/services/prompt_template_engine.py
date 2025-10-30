"""Prompt template engine for generating varied coloring page prompts.

This engine loads templates from themes/*.yml files with random variables
to create diverse prompts while maintaining consistency within the same generation (via seed).

Templates are NO LONGER hardcoded - they are loaded from YAML files.
"""

import logging
import random
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Template for generating prompts with random variations.

    Attributes:
        base_structure: Base prompt structure with {VARIABLE} placeholders
        variables: Dict of variable names to list of possible values
        quality_settings: Common quality/technical requirements
    """

    base_structure: str
    variables: dict[str, list[str]]
    quality_settings: str


class PromptTemplateEngine:
    """Engine for generating varied prompts from templates.

    Templates are loaded from themes/*.yml files (coloring_page_templates section).
    """

    def __init__(self, seed: int | None = None, themes_directory: Path | None = None):
        """Initialize template engine.

        Args:
            seed: Random seed for reproducibility (optional)
            themes_directory: Path to themes/ directory (auto-detected if None)
        """
        self.seed = seed
        self._rng = random.Random(seed)  # noqa: S311 - Not used for cryptography

        # Auto-detect themes directory if not specified
        if themes_directory is None:
            # Try to find config/branding/themes/ directory from current file location
            current_file = Path(__file__)
            project_root = current_file
            while project_root.parent != project_root:
                themes_path = project_root / "config" / "branding" / "themes"
                if themes_path.exists():
                    themes_directory = themes_path
                    break
                project_root = project_root.parent

        if themes_directory is None or not themes_directory.exists():
            raise FileNotFoundError(f"Themes directory not found: {themes_directory}")

        self.themes_directory = themes_directory
        logger.info(f"PromptTemplateEngine initialized with themes from: {themes_directory}")

    def load_template_from_yaml(self, theme_id: str) -> PromptTemplate:
        """Load prompt template from theme YAML file.

        Args:
            theme_id: Theme ID (e.g., "dinosaurs", "unicorns")

        Returns:
            PromptTemplate loaded from YAML

        Raises:
            FileNotFoundError: If theme file doesn't exist
            ValueError: If template is missing from YAML
        """
        theme_file = self.themes_directory / f"{theme_id}.yml"

        if not theme_file.exists():
            raise FileNotFoundError(f"Theme file not found: {theme_file}")

        with open(theme_file, encoding="utf-8") as f:
            theme_data = yaml.safe_load(f)

        # Check if coloring_page_templates section exists
        if "coloring_page_templates" not in theme_data:
            raise ValueError(
                f"Theme '{theme_id}' missing 'coloring_page_templates' section in {theme_file}"
            )

        templates = theme_data["coloring_page_templates"]

        return PromptTemplate(
            base_structure=templates["base_structure"],
            variables=templates["variables"],
            quality_settings=templates["quality_settings"],
        )

    def generate_prompts(self, theme: str, count: int, audience: str | None = None) -> list[str]:
        """Generate varied prompts for coloring pages.

        Args:
            theme: Theme name (e.g., "dinosaurs", "unicorns")
            count: Number of prompts to generate
            audience: Target audience ("children" or "adults") - optional

        Returns:
            List of complete prompts ready for image generation
        """
        # Load template from YAML
        template = self._find_template(theme)

        logger.info(
            f"Generating {count} prompts for theme '{theme}' "
            f"(audience={audience}, seed={self.seed})"
        )

        prompts = []
        for i in range(count):
            # Generate prompt with random variables
            prompt = self._generate_single_prompt(template, i, audience)
            prompts.append(prompt)

            # Log first and last for debugging
            if i == 0 or i == count - 1:
                logger.debug(f"Prompt {i+1}/{count}: {prompt[:150]}...")

        return prompts

    def _find_template(self, theme: str) -> PromptTemplate:
        """Find template matching the theme.

        Loads from YAML file. Supports:
        - Exact match: "dinosaurs" -> dinosaurs.yml
        - Partial match: "dino" -> dinosaurs.yml
        - Falls back to neutral-default if not found

        Args:
            theme: Theme to search for (ID or partial match)

        Returns:
            Matching template or fallback
        """
        # Normalize theme input
        theme_normalized = theme.lower().strip()

        # Try exact match first
        try:
            return self.load_template_from_yaml(theme_normalized)
        except (FileNotFoundError, ValueError):
            pass  # Try partial match

        # Try partial match (e.g., "dino" matches "dinosaurs")
        try:
            for theme_file in self.themes_directory.glob("*.yml"):
                theme_id = theme_file.stem
                if theme_normalized in theme_id or theme_id in theme_normalized:
                    logger.info(f"Theme '{theme}' matched to '{theme_id}' (partial match)")
                    return self.load_template_from_yaml(theme_id)
        except Exception as e:
            logger.debug(f"Error during theme template search: {e}. Continuing to fallback.")

        # No match found
        logger.warning(
            f"No template found for theme '{theme}'. " f"Falling back to neutral-default"
        )

        # Fallback to neutral-default
        try:
            return self.load_template_from_yaml("neutral-default")
        except (FileNotFoundError, ValueError) as e:
            # Ultimate fallback - hardcoded generic template
            logger.error(
                f"Failed to load neutral-default template: {e}. " f"Using hardcoded fallback"
            )
            return PromptTemplate(
                base_structure=(
                    "Line art coloring page of {SUBJECT} in a {ENV}, {SHOT}, {COMPOSITION}."
                ),
                variables={
                    "SHOT": ["close-up", "medium", "wide"],
                    "SUBJECT": ["simple character", "cute animal", "friendly object"],
                    "ENV": ["simple background", "nature scene", "minimal setting"],
                    "COMPOSITION": ["centered", "left-facing", "right-facing", "front view"],
                },
                quality_settings=(
                    "Black and white line art coloring page style. "
                    "IMPORTANT: Use ONLY black lines on white background, "
                    "NO colors, NO gray shading. "
                    "Bold clean outlines, closed shapes, thick black lines. "
                    "NO FRAME, NO BORDER around the illustration. "
                    "Illustration extends naturally to image boundaries. "
                    "Printable 300 DPI, simple detail for kids age 4-8. "
                    "No text, no logo, no watermark."
                ),
            )

    def _generate_single_prompt(
        self, template: PromptTemplate, index: int, audience: str | None
    ) -> str:
        """Generate a single prompt from template.

        Args:
            template: Template to use
            index: Index of prompt (for variation)
            audience: Target audience ("children" or "adults")

        Returns:
            Complete prompt string
        """
        # Create a copy of base structure
        prompt = template.base_structure

        # Replace each variable with random choice
        for var_name, options in template.variables.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in prompt:
                # Use index + var_name hash for deterministic variety across pages
                choice = self._choose_value(options, index, var_name)
                prompt = prompt.replace(placeholder, choice)

        # Add quality settings (no age-specific customization needed)
        # Quality is defined in theme YAML and applies to audience
        quality = template.quality_settings

        full_prompt = f"{prompt} {quality}"

        return full_prompt

    def _choose_value(self, options: list[str], index: int, var_name: str) -> str:
        """Choose value from options with deterministic randomness.

        Args:
            options: List of possible values
            index: Page index
            var_name: Variable name (for additional entropy)

        Returns:
            Chosen value
        """
        if self.seed is None:
            # If no seed specified, use truly random selection
            return self._rng.choice(options)
        else:
            # Create deterministic but varied seed per variable per page
            # This ensures different pages get different combinations
            page_seed = self.seed + index * 1000 + hash(var_name) % 1000
            page_rng = random.Random(page_seed)  # noqa: S311 - Not for cryptography
            return page_rng.choice(options)
