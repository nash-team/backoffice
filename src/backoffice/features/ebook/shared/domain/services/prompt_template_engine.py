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
class CharacterProfile:
    """Profile defining valid actions and environments for a character/species.

    Used to prevent incoherent combinations like:
    - "T-Rex flying" (dinosaurs)
    - "baby unicorn flying" (only winged unicorns fly)
    - "parrot steering ship" (parrots can't steer)
    """

    actions: list[str]
    environments: list[str]


# Backward compatibility alias
SpeciesProfile = CharacterProfile


@dataclass
class PromptTemplate:
    """Template for generating prompts with random variations.

    Attributes:
        base_structure: Base prompt structure with {VARIABLE} placeholders
        variables: Dict of variable names to list of possible values
        quality_settings: Common quality/technical requirements
        workflow_params: Free-form dict for workflow-specific params (ComfyUI, etc.)
        species_profiles: Optional dict mapping species to their valid actions/environments
    """

    base_structure: str
    variables: dict[str, list[str]]
    quality_settings: str
    workflow_params: dict[str, str | float | int] | None = None
    species_profiles: dict[str, SpeciesProfile] | None = None


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

    def load_template_from_yaml(self, theme_id: str, template_key: str | None = None, template_type: str = "coloring_page") -> PromptTemplate:
        """Load prompt template from theme YAML file.

        Args:
            theme_id: Theme ID (e.g., "dinosaurs", "unicorns")
            template_key: Template key (e.g., "comfy", "default", "gemini") - optional
            template_type: Type of template ("coloring_page" or "cover")

        Returns:
            PromptTemplate loaded from YAML (template-specific or default)

        Raises:
            FileNotFoundError: If theme file doesn't exist
            ValueError: If template is missing from YAML
        """
        theme_file = self.themes_directory / f"{theme_id}.yml"

        if not theme_file.exists():
            raise FileNotFoundError(f"Theme file not found: {theme_file}")

        with open(theme_file, encoding="utf-8") as f:
            theme_data = yaml.safe_load(f)

        # Determine section name based on template type
        section_name = "coloring_page_templates" if template_type == "coloring_page" else "cover_templates"

        # Check if section exists
        if section_name not in theme_data:
            raise ValueError(f"Theme '{theme_id}' missing '{section_name}' section in {theme_file}")

        templates = theme_data[section_name]

        # Try to load template by key first, then fallback to default
        if template_key and template_key in templates:
            logger.info(f"Using {template_type} template '{template_key}' in theme '{theme_id}'")
            template_data = templates[template_key]
        elif "default" in templates:
            logger.info(f"Template '{template_key}' not found, " f"using default {template_type} template for theme '{theme_id}'")
            template_data = templates["default"]
        else:
            raise ValueError(f"Theme '{theme_id}' has no template for '{template_key}' " f"and no default template in {section_name}")

        # Handle old format (prompt_blocks for cover) vs new format
        if template_type == "cover" and "prompt_blocks" in template_data:
            # Old format: assemble from blocks
            blocks = template_data["prompt_blocks"]
            prompt = f"{blocks['subject']}, {blocks['environment']}, {blocks['tone']}. " f"{', '.join(blocks['positives'])}"
            return PromptTemplate(
                base_structure=prompt,
                variables={},
                quality_settings="",
                workflow_params={"negative": ", ".join(blocks["negatives"])},
            )
        elif "prompt" in template_data:
            # Direct prompt (for diffusers/SDXL with short CLIP-friendly prompts)
            # Works for both cover and coloring_page templates
            logger.info(f"Using direct prompt for {template_type} (no variable expansion)")
            return PromptTemplate(
                base_structure=template_data["prompt"],
                variables={},  # No variables = prompt used as-is
                quality_settings="",  # Already included in prompt
                workflow_params=template_data.get("workflow_params", None),
            )
        else:
            # Coloring page format with variables (base_structure + variables + quality_settings)
            # Parse species_profiles if present (for semantic constraints)
            species_profiles = None
            if "species_profiles" in template_data:
                species_profiles = {}
                for species_name, profile_data in template_data["species_profiles"].items():
                    species_profiles[species_name] = SpeciesProfile(
                        actions=profile_data.get("actions", []),
                        environments=profile_data.get("environments", []),
                    )
                logger.info(f"Loaded species_profiles with {len(species_profiles)} species")

            return PromptTemplate(
                base_structure=template_data["base_structure"],
                variables=template_data["variables"],
                quality_settings=template_data["quality_settings"],
                workflow_params=template_data.get("workflow_params", None),
                species_profiles=species_profiles,
            )

    def generate_prompts(
        self,
        theme: str,
        count: int,
        audience: str | None = None,
        template_key: str | None = None,
    ) -> list[str]:
        """Generate varied prompts for coloring pages.

        Args:
            theme: Theme name (e.g., "dinosaurs", "unicorns")
            count: Number of prompts to generate
            audience: Target audience ("children" or "adults") - optional
            template_key: Template key (e.g., "comfy", "default") - optional

        Returns:
            List of complete prompts ready for image generation
        """
        # Load template from YAML
        template = self._find_template(theme, template_key=template_key)

        logger.info(f"Generating {count} prompts for theme '{theme}' " f"(template_key={template_key}, audience={audience}, seed={self.seed})")

        prompts = []
        for i in range(count):
            # Generate prompt with random variables
            prompt = self._generate_single_prompt(template, i, audience)
            prompts.append(prompt)

            # Log first and last for debugging
            if i == 0 or i == count - 1:
                logger.debug(f"Prompt {i+1}/{count}: {prompt[:150]}...")

        return prompts

    def generate_prompts_with_params(
        self,
        theme: str,
        count: int,
        audience: str | None = None,
        template_key: str | None = None,
    ) -> dict[str, list[str] | dict[str, str | float | int]]:
        """Generate varied prompts with workflow params.

        Args:
            theme: Theme name (e.g., "dinosaurs", "unicorns")
            count: Number of prompts to generate
            audience: Target audience ("children" or "adults") - optional
            template_key: Template key (e.g., "comfy", "default") - optional

        Returns:
            Dict with "prompts" (list of strings) and "workflow_params" (dict)
        """
        # Load template from YAML
        template = self._find_template(theme, template_key=template_key)

        logger.info(f"Generating {count} prompts with params for theme '{theme}' " f"(template_key={template_key}, audience={audience}, seed={self.seed})")

        prompts = []
        for i in range(count):
            # Generate prompt with random variables
            prompt = self._generate_single_prompt(template, i, audience)
            prompts.append(prompt)

            # Log first and last for debugging
            if i == 0 or i == count - 1:
                logger.debug(f"Prompt {i+1}/{count}: {prompt[:150]}...")

        return {
            "prompts": prompts,
            "workflow_params": template.workflow_params or {},
        }

    def generate_cover_prompt(self, theme: str, template_key: str | None = None) -> dict[str, str | dict[str, str | float | int]]:
        """Generate cover prompt with workflow params.

        Args:
            theme: Theme name (e.g., "dinosaurs", "unicorns")
            template_key: Template key (e.g., "comfy", "default") - optional

        Returns:
            Dict with "prompt" (string) and "workflow_params" (dict)
        """
        # Load cover template from YAML
        template = self._find_template(theme, template_key=template_key, template_type="cover")

        logger.info(f"Generating cover prompt for theme '{theme}' (template_key={template_key})")

        # Cover prompts don't have variables (or have empty variables)
        prompt = template.base_structure
        if template.quality_settings:
            prompt = f"{prompt} {template.quality_settings}"

        return {
            "prompt": prompt,
            "workflow_params": template.workflow_params or {},
        }

    def _find_template(self, theme: str, template_key: str | None = None, template_type: str = "coloring_page") -> PromptTemplate:
        """Find template matching the theme and template key.

        Loads from YAML file. Supports:
        - Exact match: "dinosaurs" -> dinosaurs.yml
        - Partial match: "dino" -> dinosaurs.yml
        - Template-specific templates with fallback to default
        - Falls back to neutral-default if theme not found

        Args:
            theme: Theme to search for (ID or partial match)
            template_key: Template key (e.g., "comfy", "default") - optional
            template_type: Type of template ("coloring_page" or "cover")

        Returns:
            Matching template or fallback
        """
        # Normalize theme input
        theme_normalized = theme.lower().strip()

        # Try exact match first
        try:
            return self.load_template_from_yaml(theme_normalized, template_key, template_type)
        except (FileNotFoundError, ValueError):
            pass  # Try partial match

        # Try partial match (e.g., "dino" matches "dinosaurs")
        try:
            for theme_file in self.themes_directory.glob("*.yml"):
                theme_id = theme_file.stem
                if theme_normalized in theme_id or theme_id in theme_normalized:
                    logger.info(f"Theme '{theme}' matched to '{theme_id}' (partial match)")
                    return self.load_template_from_yaml(theme_id, template_key, template_type)
        except Exception as e:
            logger.debug(f"Error during theme template search: {e}. Continuing to fallback.")

        # No match found - raise error instead of silent fallback
        raise FileNotFoundError(f"No template found for theme '{theme}'. Available themes: " f"{', '.join([f.stem for f in self.themes_directory.glob('*.yml')])}")

    def _generate_single_prompt(self, template: PromptTemplate, index: int, audience: str | None) -> str:
        """Generate a single prompt from template.

        Uses species_profiles (if defined) to ensure semantically valid combinations.
        For example, prevents "T-Rex flying" or "Pteranodon swimming".

        Args:
            template: Template to use
            index: Index of prompt (for variation)
            audience: Target audience ("children" or "adults")

        Returns:
            Complete prompt string
        """
        # Create a copy of base structure
        prompt = template.base_structure

        # Add a short audience hint to steer the model
        if audience:
            audience_hints = {
                "children": "For a children's coloring book: simple bold lines, clear shapes, kid-friendly composition.",
                "adults": "For an adult coloring book: intricate, elegant line work with rich details.",
            }
            hint = audience_hints.get(audience.lower())
            if hint:
                prompt = f"{prompt} {hint}"

        # If species_profiles exist, use constrained selection
        # Auto-detect which variable the profiles apply to (SPECIES, UNICORN, CHARACTER, etc.)
        profile_var = self._find_profile_variable(template)
        if template.species_profiles and profile_var:
            prompt = self._generate_with_character_constraints(template, prompt, index, profile_var)
        else:
            # Original behavior: independent random selection (backward compatible)
            for var_name, options in template.variables.items():
                placeholder = f"{{{var_name}}}"
                if placeholder in prompt:
                    choice = self._choose_value(options, index, var_name)
                    prompt = prompt.replace(placeholder, choice)

        # Add quality settings (no age-specific customization needed)
        # Quality is defined in theme YAML and applies to audience
        quality = template.quality_settings

        full_prompt = f"{prompt} {quality}"

        return full_prompt

    def _find_profile_variable(self, template: PromptTemplate) -> str | None:
        """Find which variable the species_profiles keys match.

        Auto-detects the profile variable by checking which variable's values
        overlap with the profile keys. Supports SPECIES, UNICORN, CHARACTER, etc.

        Args:
            template: Template to check

        Returns:
            Variable name if found, None otherwise
        """
        if not template.species_profiles:
            return None

        profile_keys = set(template.species_profiles.keys())

        for var_name, var_values in template.variables.items():
            # Check if there's overlap between profile keys and variable values
            if set(var_values) & profile_keys:
                return var_name

        return None

    def _generate_with_character_constraints(self, template: PromptTemplate, prompt: str, index: int, profile_var: str) -> str:
        """Generate prompt with character-specific constraints.

        Works with any profile variable (SPECIES, UNICORN, CHARACTER, etc.).

        1. Choose a character from the profile variable list
        2. Use character profile to filter valid ACTION and ENV options
        3. Replace remaining variables normally

        Args:
            template: Template with species_profiles
            prompt: Base prompt string
            index: Page index for deterministic variation
            profile_var: Name of the variable that profiles apply to (e.g., "SPECIES", "UNICORN")

        Returns:
            Prompt with all variables replaced (semantically valid)
        """
        # Step 1: Choose character from profile variable
        character_options = template.variables[profile_var]
        chosen_character = self._choose_value(character_options, index, profile_var)
        prompt = prompt.replace(f"{{{profile_var}}}", chosen_character)

        # Step 2: Get profile for this character (or use full lists as fallback)
        profile = template.species_profiles.get(chosen_character) if template.species_profiles else None

        # Step 3: Replace ACTION with character-valid options
        if "{ACTION}" in prompt and "ACTION" in template.variables:
            if profile and profile.actions:
                action_options = profile.actions
            else:
                action_options = template.variables["ACTION"]
            chosen_action = self._choose_value(action_options, index, "ACTION")
            prompt = prompt.replace("{ACTION}", chosen_action)

        # Step 4: Replace ENV with character-valid options
        if "{ENV}" in prompt and "ENV" in template.variables:
            if profile and profile.environments:
                env_options = profile.environments
            else:
                env_options = template.variables["ENV"]
            chosen_env = self._choose_value(env_options, index, "ENV")
            prompt = prompt.replace("{ENV}", chosen_env)

        # Step 5: Replace remaining variables normally (SHOT, FOCUS, COMPOSITION, etc.)
        for var_name, options in template.variables.items():
            if var_name in (profile_var, "ACTION", "ENV"):
                continue  # Already handled
            placeholder = f"{{{var_name}}}"
            if placeholder in prompt:
                choice = self._choose_value(options, index, var_name)
                prompt = prompt.replace(placeholder, choice)

        return prompt

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
