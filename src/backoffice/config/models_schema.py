"""Pydantic schemas for models.yaml configuration validation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ModelMapping(BaseModel):
    """Schema for individual model configuration.

    Validates provider-specific constraints:
    - All providers require a model name
    - Provider must be one of the supported types

    Note: This replaces the dataclass version in model_registry.py
    """

    provider: Literal["openrouter", "gemini", "comfy"] = Field(..., description="Image generation provider")
    model: str = Field(
        ...,
        min_length=1,
        description="Model identifier (e.g., google/gemini-2.5-flash-image-preview)",
    )
    supports_vectorization: bool = Field(False, description="Whether model supports SVG/vector output")

    class Config:
        """Pydantic config."""

        frozen = True  # Make immutable like dataclass


class ModelsConfig(BaseModel):
    """Schema for models.yaml root configuration.

    Ensures required model types are present:
    - cover: For cover generation
    - coloring_page: For content page generation
    """

    models: dict[str, ModelMapping] = Field(..., description="Model configurations by type")

    @field_validator("models")
    @classmethod
    def validate_required_model_types(cls, v: dict[str, ModelMapping]) -> dict[str, ModelMapping]:
        """Ensure required model types are configured."""
        required_types = {"cover", "coloring_page"}
        configured_types = set(v.keys())
        missing_types = required_types - configured_types

        if missing_types:
            raise ValueError(f"Missing required model types in configuration: {sorted(missing_types)}. " f"Please configure all required types: {sorted(required_types)}")

        return v
