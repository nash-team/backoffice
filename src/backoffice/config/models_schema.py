"""Pydantic schemas for models.yaml configuration validation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ModelMapping(BaseModel):
    """Schema for individual model configuration.

    Validates provider-specific constraints:
    - LoRA/ControlNet only supported with 'local' provider
    - All providers require a model name
    - Provider must be one of the supported types

    Note: This replaces the dataclass version in model_registry.py
    """

    provider: Literal["openrouter", "gemini", "comfy"] = Field(
        ..., description="Image generation provider"
    )
    model: str = Field(
        ...,
        min_length=1,
        description="Model identifier (e.g., google/gemini-2.5-flash-image-preview)",
    )
    lora: str | None = Field(None, description="LoRA adapter ID (local provider only)")
    controlnet: str | None = Field(None, description="ControlNet model ID (local provider only)")
    supports_vectorization: bool = Field(False, description="Whether model supports SVG/vector output")

    class Config:
        """Pydantic config."""

        frozen = True  # Make immutable like dataclass

    @field_validator("lora")
    @classmethod
    def validate_lora_local_only(cls, v: str | None, info) -> str | None:
        """Validate that LoRA is only used with local provider."""
        if v is not None:
            provider = info.data.get("provider")
            if provider != "local":
                raise ValueError(f"LoRA adapters are only supported with 'local' provider, got '{provider}'. " f"Remove 'lora' field or change provider to 'local'.")
        return v

    @field_validator("controlnet")
    @classmethod
    def validate_controlnet_local_only(cls, v: str | None, info) -> str | None:
        """Validate that ControlNet is only used with local provider."""
        if v is not None:
            provider = info.data.get("provider")
            if provider != "local":
                raise ValueError(f"ControlNet is only supported with 'local' provider, got '{provider}'. " f"Remove 'controlnet' field or change provider to 'local'.")
        return v


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
