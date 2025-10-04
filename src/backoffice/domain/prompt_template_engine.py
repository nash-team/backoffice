"""Prompt template engine for generating varied coloring page prompts.

This engine uses templates with random variables to create diverse prompts
while maintaining consistency within the same generation (via seed).
"""

import logging
import random
from dataclasses import dataclass

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
    """Engine for generating varied prompts from templates."""

    # Default theme templates (matching themes/*.yml)
    THEMES = {
        "dinosaurs": PromptTemplate(
            base_structure=(
                "Line art coloring page of a {SPECIES} {ACTION} in a {ENV}, "
                "{SHOT}, {FOCUS}, {COMPOSITION}."
            ),
            variables={
                "SHOT": ["close-up", "medium", "wide", "silhouette"],
                "SPECIES": [
                    "T-Rex",
                    "Triceratops",
                    "Diplodocus",
                    "Stegosaurus",
                    "Pteranodon",
                    "Ankylosaurus",
                    "Velociraptor",
                    "Brachiosaurus",
                ],
                "ACTION": [
                    "roaring",
                    "eating leaves",
                    "running",
                    "sleeping",
                    "hatching",
                    "playing",
                    "swimming",
                    "flying",
                ],
                "ENV": [
                    "lush jungle",
                    "volcanic plain",
                    "riverbank",
                    "tropical forest",
                    "desert",
                    "prehistoric landscape",
                    "mountains",
                ],
                "FOCUS": [
                    "head",
                    "full body",
                    "group of 2-3",
                    "parent & baby",
                    "footprint pattern",
                ],
                "COMPOSITION": ["left-facing", "right-facing", "front", "3/4 view", "top-down"],
            },
            quality_settings=(
                "Black and white line art coloring page style. "
                "IMPORTANT: Use ONLY black lines on white background, NO colors, NO gray shading. "
                "Bold clean outlines, closed shapes, thick black lines. "
                "NO FRAME, NO BORDER around the illustration. "
                "Illustration extends naturally to image boundaries. "
                "Printable 300 DPI, simple to medium detail for kids age 4-8. "
                "No text, no logo, no watermark."
            ),
        ),
        "unicorns": PromptTemplate(
            base_structure=(
                "Line art coloring page of a {UNICORN} {ACTION} in a {ENV}, "
                "{SHOT}, {FOCUS}, {COMPOSITION}."
            ),
            variables={
                "SHOT": ["close-up", "medium", "wide", "magical scene"],
                "UNICORN": [
                    "cute magical unicorn",
                    "unicorn with rainbow mane",
                    "unicorn with sparkling wings",
                    "baby unicorn",
                    "elegant unicorn",
                    "playful unicorn",
                ],
                "ACTION": [
                    "prancing",
                    "flying",
                    "playing",
                    "resting",
                    "dancing",
                    "jumping over rainbow",
                    "spreading sparkles",
                ],
                "ENV": [
                    "enchanted landscape",
                    "soft clouds",
                    "magical meadow",
                    "starry sky",
                    "flower garden",
                    "rainbow bridge",
                    "crystal castle background",
                ],
                "FOCUS": [
                    "head with horn",
                    "full body",
                    "with butterflies",
                    "with stars",
                    "with flowers",
                ],
                "COMPOSITION": ["left-facing", "right-facing", "front", "3/4 view", "jumping"],
            },
            quality_settings=(
                "Black and white line art coloring page style. "
                "IMPORTANT: Use ONLY black lines on white background, NO colors, NO gray shading. "
                "Bold clean outlines, closed shapes, thick black lines. "
                "NO FRAME, NO BORDER around the illustration. "
                "Illustration extends naturally to image boundaries. "
                "Printable 300 DPI, simple to medium detail for kids age 4-8. "
                "No text, no logo, no watermark."
            ),
        ),
        "pirates": PromptTemplate(
            base_structure=(
                "Line art coloring page of a {CHARACTER} {ACTION} in a {ENV}, "
                "{SHOT}, {FOCUS}, {COMPOSITION}."
            ),
            variables={
                "SHOT": ["close-up", "medium", "wide", "action scene"],
                "CHARACTER": [
                    "friendly cartoon pirate",
                    "pirate captain with hat",
                    "young pirate kid",
                    "pirate crew member",
                    "parrot companion",
                    "pirate with treasure map",
                ],
                "ACTION": [
                    "searching for treasure",
                    "sailing",
                    "digging for treasure",
                    "looking through telescope",
                    "celebrating",
                    "climbing rigging",
                    "steering ship",
                ],
                "ENV": [
                    "pirate ship deck",
                    "treasure island",
                    "beach with palm trees",
                    "ocean waves",
                    "treasure cave",
                    "dock",
                    "tropical island",
                ],
                "FOCUS": [
                    "pirate with treasure chest",
                    "full body",
                    "with ship",
                    "with parrot",
                    "with flag",
                ],
                "COMPOSITION": ["left-facing", "right-facing", "front", "3/4 view", "action pose"],
            },
            quality_settings=(
                "Bold clean outlines, closed shapes, no shading, no gray, no color. "
                "NO FRAME, NO BORDER around the illustration. "
                "Illustration extends naturally to image boundaries. "
                "Printable 300 DPI, simple to medium detail for kids age 4-8. "
                "No text, no logo, no watermark, no scary elements, no violence."
            ),
        ),
    }

    # Generic fallback template
    GENERIC_TEMPLATE = PromptTemplate(
        base_structure="Line art coloring page of {SUBJECT} in a {ENV}, {SHOT}, {COMPOSITION}.",
        variables={
            "SHOT": ["close-up", "medium", "wide"],
            "SUBJECT": ["simple character", "object", "scene"],
            "ENV": ["simple background", "nature scene", "indoor scene"],
            "COMPOSITION": ["centered", "left-side", "right-side", "diagonal"],
        },
        quality_settings=(
            "Bold clean outlines, closed shapes, no shading, no gray, no color. "
            "NO FRAME, NO BORDER around the illustration. "
            "Illustration extends naturally to image boundaries. "
            "Printable 300 DPI, simple detail for kids age 4-8. "
            "No text, no logo, no watermark."
        ),
    )

    def __init__(self, seed: int | None = None):
        """Initialize template engine.

        Args:
            seed: Random seed for reproducibility (optional)
        """
        self.seed = seed
        self._rng = random.Random(seed)  # noqa: S311 - Not used for cryptography

    def generate_prompts(self, theme: str, count: int, age_group: str | None = None) -> list[str]:
        """Generate varied prompts for coloring pages.

        Args:
            theme: Theme name (e.g., "dinosaures", "animaux")
            count: Number of prompts to generate
            age_group: Target age group (e.g., "4-6", "7-9") - optional

        Returns:
            List of complete prompts ready for image generation
        """
        # Find matching template (case-insensitive, partial match)
        template = self._find_template(theme)

        template_type = "found" if template != self.GENERIC_TEMPLATE else "generic"
        logger.info(
            f"Generating {count} prompts for theme '{theme}' "
            f"(seed={self.seed}, template={template_type})"
        )

        prompts = []
        for i in range(count):
            # Generate prompt with random variables
            prompt = self._generate_single_prompt(template, i, age_group)
            prompts.append(prompt)

            # Log first and last for debugging
            if i == 0 or i == count - 1:
                logger.debug(f"Prompt {i+1}/{count}: {prompt[:150]}...")

        return prompts

    def _find_template(self, theme: str) -> PromptTemplate:
        """Find template matching the theme.

        Supports matching by:
        - Exact ID match (e.g., "dinosaurs")
        - Label match (e.g., "Dinosaures" -> "dinosaurs")
        - Partial match (e.g., "dino" -> "dinosaurs")

        Args:
            theme: Theme to search for (ID or label)

        Returns:
            Matching template or generic fallback
        """
        # Normalize theme input
        theme_normalized = theme.lower().strip()

        # Label to ID mapping (for compatibility with theme/*.yml files)
        label_to_id = {
            "dinosaures": "dinosaurs",
            "licornes": "unicorns",
            "pirates": "pirates",
        }

        # Try label mapping first
        if theme_normalized in label_to_id:
            mapped_id = label_to_id[theme_normalized]
            logger.info(f"Theme label '{theme}' mapped to ID '{mapped_id}'")
            return self.THEMES[mapped_id]

        # Exact match by ID
        if theme_normalized in self.THEMES:
            return self.THEMES[theme_normalized]

        # Partial match (e.g., "dino" matches "dinosaurs")
        for key, template in self.THEMES.items():
            if theme_normalized in key or key in theme_normalized:
                logger.info(f"Theme '{theme}' matched to template '{key}' (partial match)")
                return template

        # Fallback to generic
        logger.warning(f"No template found for theme '{theme}', using generic template")
        return self.GENERIC_TEMPLATE

    def _generate_single_prompt(
        self, template: PromptTemplate, index: int, age_group: str | None
    ) -> str:
        """Generate a single prompt from template.

        Args:
            template: Template to use
            index: Index of prompt (for variation)
            age_group: Target age group

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

        # Add quality settings
        quality = template.quality_settings
        if age_group:
            quality = quality.replace("age 4-8", f"age {age_group}")

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
