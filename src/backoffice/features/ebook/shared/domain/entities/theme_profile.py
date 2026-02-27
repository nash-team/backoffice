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


class BackCoverConfigModel(BaseModel):
    """Back cover overlay configuration"""

    preview_pages: list[int] = Field(..., min_length=2, max_length=2, description="Indices of 2 content pages to show as previews")
    tagline: str = Field(..., min_length=1, description="Bold tagline text")
    description: str = Field(..., min_length=1, description="Description paragraph")
    author: str = Field(..., min_length=1, description="Author name")
    publisher: str = Field(..., min_length=1, description="Publisher name")
    isbn: str | None = Field(default=None, description="ISBN-13 for EAN barcode on back cover")

    @field_validator("isbn")
    @classmethod
    def validate_isbn_13(cls, v: str | None) -> str | None:
        """Validate ISBN-13: 13 digits, 978/979 prefix, valid check digit."""
        if v is None:
            return None
        digits = v.replace("-", "").replace(" ", "")
        if len(digits) != 13:
            raise ValueError("ISBN must be exactly 13 digits")
        if not digits.isdigit():
            raise ValueError("ISBN must contain only digits (and optional hyphens)")
        if not digits.startswith(("978", "979")):
            raise ValueError("ISBN-13 must start with 978 or 979")
        # ISBN-13 check digit algorithm: alternate weights 1 and 3
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
        expected_check = (10 - (total % 10)) % 10
        if int(digits[12]) != expected_check:
            raise ValueError(f"Invalid ISBN-13 check digit: expected {expected_check}, got {digits[12]}")
        return digits  # Store normalized (digits only)


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
    cover_title_image: str = Field(..., min_length=1, description="Path to cover title PNG (transparent)")
    cover_footer_image: str = Field(..., min_length=1, description="Path to cover footer PNG (transparent)")
    cover_templates: dict[str, CoverTemplateModel] = Field(..., min_length=1)
    coloring_page_templates: dict[str, ColoringPageTemplateModel] = Field(default_factory=dict)
    back_cover: BackCoverConfigModel | None = None

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
class BackCoverConfig:
    """Domain entity for back cover overlay configuration"""

    preview_pages: list[int]
    tagline: str
    description: str
    author: str
    publisher: str
    isbn: str | None = None


@dataclass
class ThemeProfile:
    """Domain entity for complete theme profile"""

    id: str
    label: str
    palette: Palette
    blocks: PromptBlocks
    cover_title_image: str
    cover_footer_image: str
    back_cover: BackCoverConfig | None = None

    @classmethod
    def from_model(cls, model: ThemeProfileModel) -> "ThemeProfile":
        """Create ThemeProfile from Pydantic model

        Extracts prompt_blocks from the default cover template.
        """
        # Extract prompt_blocks from default cover template
        default_cover = model.cover_templates["default"]
        if not default_cover.prompt_blocks:
            raise ValueError(f"Theme {model.id}: default cover template must have prompt_blocks")

        back_cover = None
        if model.back_cover:
            back_cover = BackCoverConfig(
                preview_pages=model.back_cover.preview_pages,
                tagline=model.back_cover.tagline,
                description=model.back_cover.description,
                author=model.back_cover.author,
                publisher=model.back_cover.publisher,
                isbn=model.back_cover.isbn,
            )

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
            cover_title_image=model.cover_title_image,
            cover_footer_image=model.cover_footer_image,
            back_cover=back_cover,
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
