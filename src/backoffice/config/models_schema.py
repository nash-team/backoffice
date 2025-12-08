"""Pydantic schemas for models.yaml configuration validation."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelMapping(BaseModel):
    """Schema for individual model configuration.

    Validates provider-specific constraints:
    - All providers require a model name
    - Provider must be one of the supported types
    - controlnet/lora/lora_weight are only valid for diffusers provider
    """

    provider: Literal["openrouter", "gemini", "comfy", "diffusers"] = Field(..., description="Image generation provider")
    model: str = Field(
        ...,
        min_length=1,
        description="Model identifier (HF ID, local path, or workflow ID)",
    )
    supports_vectorization: bool = False

    # Diffusers-only options
    controlnet: str | None = None
    lora: str | None = None
    lora_weight: float = Field(0.7, ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_provider_specific_fields(self) -> Self:
        """Validate that diffusers-only fields aren't set for other providers."""
        if self.provider != "diffusers":
            if self.controlnet is not None:
                raise ValueError("controlnet is only supported when provider='diffusers'")
            if self.lora is not None:
                raise ValueError("lora is only supported when provider='diffusers'")
            # lora_weight default is fine, ignored for non-diffusers

        return self


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
            raise ValueError(f"Missing required model types: {sorted(missing_types)}. " f"Required: {sorted(required_types)}")

        return v
