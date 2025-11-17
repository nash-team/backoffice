"""Unit tests for models.yaml Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from backoffice.config.models_schema import ModelMapping, ModelsConfig


class TestModelMapping:
    """Tests for ModelMapping schema validation."""

    def test_valid_openrouter_config(self):
        """Valid OpenRouter config should pass validation."""
        mapping = ModelMapping(
            provider="openrouter",
            model="google/gemini-2.5-flash-image-preview",
            supports_vectorization=False,
        )
        assert mapping.provider == "openrouter"
        assert mapping.model == "google/gemini-2.5-flash-image-preview"

    def test_valid_gemini_config(self):
        """Valid Gemini config should pass validation."""
        mapping = ModelMapping(
            provider="gemini",
            model="gemini-2.5-flash-image",
            supports_vectorization=False,
        )
        assert mapping.provider == "gemini"
        assert mapping.model == "gemini-2.5-flash-image"

    def test_valid_comfy_config(self):
        """Valid Comfy config should pass validation."""
        mapping = ModelMapping(
            provider="comfy",
            model="flux-dev",
            supports_vectorization=False,
        )
        assert mapping.provider == "comfy"
        assert mapping.model == "flux-dev"

    def test_invalid_provider(self):
        """Invalid provider should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMapping(
                provider="invalid_provider",  # type: ignore
                model="some-model",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "provider" in errors[0]["loc"]

    def test_empty_model_name_fails(self):
        """Empty model name should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMapping(
                provider="openrouter",
                model="",  # Empty model name
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "model" in errors[0]["loc"]

    def test_missing_required_fields(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMapping()  # type: ignore
        errors = exc_info.value.errors()
        # Should error on missing 'provider' and 'model'
        assert len(errors) == 2
        error_fields = {err["loc"][0] for err in errors}
        assert "provider" in error_fields
        assert "model" in error_fields

    def test_model_mapping_is_frozen(self):
        """ModelMapping should be immutable (frozen)."""
        mapping = ModelMapping(
            provider="openrouter",
            model="google/gemini-2.5-flash-image-preview",
        )
        with pytest.raises(ValidationError):
            mapping.provider = "gemini"  # type: ignore


class TestModelsConfig:
    """Tests for ModelsConfig schema validation."""

    def test_valid_config_with_required_types(self):
        """Valid config with required types should pass validation."""
        config = ModelsConfig(
            models={
                "cover": ModelMapping(
                    provider="openrouter",
                    model="google/gemini-2.5-flash-image-preview",
                ),
                "coloring_page": ModelMapping(
                    provider="comfy",
                    model="flux-dev",
                ),
            }
        )
        assert len(config.models) == 2
        assert "cover" in config.models
        assert "coloring_page" in config.models

    def test_missing_cover_type_fails(self):
        """Config missing 'cover' type should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelsConfig(
                models={
                    "coloring_page": ModelMapping(
                        provider="comfy",
                        model="flux-dev",
                    ),
                }
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "cover" in str(errors[0]["msg"])

    def test_missing_coloring_page_type_fails(self):
        """Config missing 'coloring_page' type should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelsConfig(
                models={
                    "cover": ModelMapping(
                        provider="openrouter",
                        model="google/gemini-2.5-flash-image-preview",
                    ),
                }
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "coloring_page" in str(errors[0]["msg"])

    def test_empty_models_dict_fails(self):
        """Empty models dict should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelsConfig(models={})
        errors = exc_info.value.errors()
        assert len(errors) == 1
        # Should mention missing required types
        assert "cover" in str(errors[0]["msg"]) or "coloring_page" in str(errors[0]["msg"])

    def test_extra_model_types_allowed(self):
        """Extra model types beyond required ones should be allowed."""
        config = ModelsConfig(
            models={
                "cover": ModelMapping(
                    provider="openrouter",
                    model="google/gemini-2.5-flash-image-preview",
                ),
                "coloring_page": ModelMapping(
                    provider="comfy",
                    model="flux-dev",
                ),
                "custom_type": ModelMapping(  # Extra type
                    provider="gemini",
                    model="gemini-2.5-flash-image",
                ),
            }
        )
        assert len(config.models) == 3
        assert "custom_type" in config.models
