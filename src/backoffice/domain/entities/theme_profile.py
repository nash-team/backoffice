from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class PaletteModel(BaseModel):
    """Palette configuration for a theme"""

    base: list[str] = Field(..., min_length=1, description="Base colors for the theme")
    accents_allowed: list[str] = Field(default_factory=list, description="Allowed accent colors")
    forbidden_keywords: list[str] = Field(
        default_factory=list, description="Forbidden color keywords"
    )

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


class ThemeProfileModel(BaseModel):
    """Complete theme profile configuration"""

    id: str = Field(..., min_length=1, pattern=r"^[a-z0-9_-]+$", description="Theme identifier")
    label: str = Field(..., min_length=1, description="Human-readable theme name")
    palette: PaletteModel
    prompt_blocks: PromptBlocksModel

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Theme ID cannot be empty")
        return v.strip().lower()


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
        """Create ThemeProfile from Pydantic model"""
        return cls(
            id=model.id,
            label=model.label,
            palette=Palette(
                base=model.palette.base,
                accents_allowed=model.palette.accents_allowed,
                forbidden_keywords=model.palette.forbidden_keywords,
            ),
            blocks=PromptBlocks(
                subject=model.prompt_blocks.subject,
                environment=model.prompt_blocks.environment,
                tone=model.prompt_blocks.tone,
                positives=model.prompt_blocks.positives,
                negatives=model.prompt_blocks.negatives,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "label": self.label,
            "palette": {
                "base": self.palette.base,
                "accents_allowed": self.palette.accents_allowed,
                "forbidden_keywords": self.palette.forbidden_keywords,
            },
            "prompt_blocks": {
                "subject": self.blocks.subject,
                "environment": self.blocks.environment,
                "tone": self.blocks.tone,
                "positives": self.blocks.positives,
                "negatives": self.blocks.negatives,
            },
        }


def load_theme_from_yaml(file_path: Path) -> ThemeProfile:
    """Load and validate theme from YAML file"""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty YAML file: {file_path}")

        # Validate using Pydantic model
        model = ThemeProfileModel(**data)

        # Convert to domain entity
        return ThemeProfile.from_model(model)

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {file_path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load theme from {file_path}: {e}") from e
