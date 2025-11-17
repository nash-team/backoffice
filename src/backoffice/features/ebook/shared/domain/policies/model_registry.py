"""Model registry for provider selection (V1 slim - YAML only)."""

import logging
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import ValidationError

from backoffice.config.models_schema import ModelMapping, ModelsConfig

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry of model mappings (V1: YAML file only, no remote/env).

    V1 simplification:
    - Single YAML file as source of truth
    - No TTL, no remote config, no env overrides
    - Simple dict lookup
    """

    _instance: ClassVar["ModelRegistry | None"] = None
    _mappings: dict[str, ModelMapping]

    def __init__(self, config_path: str | Path):
        """Initialize registry from YAML file.

        Args:
            config_path: Path to YAML configuration file
        """
        self._config_path = Path(config_path)
        self._mappings = {}
        self._load_config()

    @classmethod
    def get_instance(cls, config_path: str | Path | None = None) -> "ModelRegistry":
        """Get singleton instance.

        Args:
            config_path: Path to config (required on first call)

        Returns:
            ModelRegistry instance
        """
        if cls._instance is None:
            if config_path is None:
                # Find project root by looking for config/ directory
                current = Path(__file__).resolve()
                while current.parent != current:
                    config_dir = current / "config"
                    if config_dir.exists() and (config_dir / "generation").exists():
                        config_path = config_dir / "generation" / "models.yaml"
                        break
                    current = current.parent
                else:
                    raise FileNotFoundError("Could not find config/generation/models.yaml in project tree")
            cls._instance = cls(config_path)
        return cls._instance

    def _load_config(self) -> None:
        """Load and validate model mappings from YAML.

        Raises:
            ValidationError: If YAML config is invalid (structure, types, constraints)
            FileNotFoundError: If config file not found and defaults not applicable
        """
        if not self._config_path.exists():
            logger.warning(f"⚠️ Config file not found: {self._config_path}, using defaults")
            self._set_defaults()
            return

        try:
            # Load YAML
            with open(self._config_path) as f:
                config_data = yaml.safe_load(f)

            # Validate with Pydantic schema (raises ValidationError if invalid)
            validated_config = ModelsConfig(**config_data)

            # Extract validated mappings
            self._mappings = validated_config.models

            logger.info(f"✅ Loaded and validated {len(self._mappings)} model mappings " f"from {self._config_path}")

        except ValidationError:
            logger.error(f"❌ Invalid model configuration in {self._config_path}")
            # Re-raise with original exception info
            raise
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            raise

    def _set_defaults(self) -> None:
        """Set default model mappings (validated via Pydantic)."""
        # Use Pydantic models for consistency
        self._mappings = {
            "cover": ModelMapping(
                provider="openrouter",
                model="google/gemini-2.5-flash-image-preview",
                supports_vectorization=False,
            ),
            "coloring_page": ModelMapping(
                provider="gemini",
                model="gemini-2.5-flash-image",
                supports_vectorization=False,
            ),
        }

    def get_cover_model(self) -> ModelMapping:
        """Get model for cover generation."""
        return self._mappings.get("cover", self._mappings["cover"])

    def get_page_model(self) -> ModelMapping:
        """Get model for content page generation."""
        return self._mappings.get("coloring_page", self._mappings["coloring_page"])
