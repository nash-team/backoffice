from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class PaletteModel(BaseModel):
    """Palette configuration for a theme"""

    base: list[str] = Field(..., min_length=1, description="Base colors for the theme")
    accents_allowed: list[str] = Field(default_factory=list, description="Allowed accent colors")
    forbidden_keywords: list[str] = Field(default_factory=list, description="Forbidden color keywords")

    @field_validator("base")
    @classmethod
    def validate_base_colors(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Base colors cannot be empty")
        return v


class PromptBlocksModel(BaseModel):
    """Prompt building blocks for a theme"""

    subject: str = Field(..., min_length=1, description="Main subject description")
    environment: str = Field(..., min_length=1, description="Environment/background description")
    tone: str = Field(..., min_length=1, description="Tone and mood")
    positives: list[str] = Field(..., min_length=1, description="Positive prompt elements")
    negatives: list[str] = Field(..., min_length=1, description="Negative prompt elements")

    @field_validator("subject", "environment", "tone")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()


class CoverTemplateModel(BaseModel):
    """Cover template configuration"""

    prompt_blocks: PromptBlocksModel | None = None
    prompt: str | None = None
    workflow_params: dict[str, str] = Field(default_factory=dict)


class ColoringPageTemplateModel(BaseModel):
    """Coloring page template configuration"""

    base_structure: str | None = None
    variables: dict[str, list[str]] = Field(default_factory=dict)
    quality_settings: str | None = None
    workflow_params: dict[str, str] = Field(default_factory=dict)


class ThemeProfileModel(BaseModel):
    """Complete theme profile configuration"""

    id: str = Field(..., min_length=1, pattern=r"^[a-z0-9_-]+$", description="Theme identifier")
    label: str = Field(..., min_length=1, description="Human-readable theme name")
    palette: PaletteModel
    cover_templates: dict[str, CoverTemplateModel] = Field(..., min_length=1)
    coloring_page_templates: dict[str, ColoringPageTemplateModel] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Theme ID cannot be empty")
        return v.strip().lower()

    @field_validator("cover_templates")
    @classmethod
    def validate_cover_templates(cls, v: dict[str, CoverTemplateModel]) -> dict[str, CoverTemplateModel]:
        if "default" not in v:
            raise ValueError("cover_templates must contain a 'default' template")
        if v["default"].prompt_blocks is None:
            raise ValueError("cover_templates.default must have prompt_blocks")
        return v


@dataclass
class Palette:
    """Domain entity for theme palette"""

    base: list[str]
    accents_allowed: list[str]
    forbidden_keywords: list[str]


@dataclass
class PromptBlocks:
    """Domain entity for prompt building blocks"""

    subject: str
    environment: str
    tone: str
    positives: list[str]
    negatives: list[str]


@dataclass
class ThemeProfile:
    """Domain entity for complete theme profile"""

    id: str
    label: str
    palette: Palette
    blocks: PromptBlocks

    @classmethod
    def from_model(cls, model: ThemeProfileModel) -> "ThemeProfile":
        """Create ThemeProfile from Pydantic model

        Extracts prompt_blocks from the default cover template.
        """
        # Extract prompt_blocks from default cover template
        default_cover = model.cover_templates["default"]
        if not default_cover.prompt_blocks:
            raise ValueError(f"Theme {model.id}: default cover template must have prompt_blocks")

        return cls(
            id=model.id,
            label=model.label,
            palette=Palette(
                base=model.palette.base,
                accents_allowed=model.palette.accents_allowed,
                forbidden_keywords=model.palette.forbidden_keywords,
            ),
            blocks=PromptBlocks(
                subject=default_cover.prompt_blocks.subject,
                environment=default_cover.prompt_blocks.environment,
                tone=default_cover.prompt_blocks.tone,
                positives=default_cover.prompt_blocks.positives,
                negatives=default_cover.prompt_blocks.negatives,
            ),
        )


def load_theme_from_yaml(file_path: Path) -> ThemeProfile:
    """Load and validate theme from YAML file

    Expects theme structure with cover_templates.default.prompt_blocks.
    """
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty YAML file: {file_path}")

        # Validate using Pydantic model (includes validation of required structure)
        model = ThemeProfileModel(**data)

        # Convert to domain entity
        return ThemeProfile.from_model(model)

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {file_path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load theme from {file_path}: {e}") from e
