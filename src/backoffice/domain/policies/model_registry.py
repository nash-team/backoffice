"""Model registry for provider selection (V1 slim - YAML only)."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ModelMapping:
    """Model configuration."""

    provider: str
    model: str
    supports_vectorization: bool = False


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
                config_path = Path(__file__).parent.parent.parent / "config" / "models.yaml"
            cls._instance = cls(config_path)
        return cls._instance

    def _load_config(self) -> None:
        """Load model mappings from YAML."""
        if not self._config_path.exists():
            logger.warning(f"⚠️ Config file not found: {self._config_path}, using defaults")
            self._set_defaults()
            return

        try:
            with open(self._config_path) as f:
                config = yaml.safe_load(f)

            for key, value in config.get("models", {}).items():
                self._mappings[key] = ModelMapping(
                    provider=value["provider"],
                    model=value["model"],
                    supports_vectorization=value.get("supports_vectorization", False),
                )

            logger.info(f"✅ Loaded {len(self._mappings)} model mappings from {self._config_path}")

        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}, using defaults")
            self._set_defaults()

    def _set_defaults(self) -> None:
        """Set default model mappings."""
        self._mappings = {
            "cover": ModelMapping(
                provider="openrouter",
                model="google/gemini-2.5-flash-image-preview",
                supports_vectorization=False,
            ),
            "coloring_page": ModelMapping(
                provider="huggingface",  # Free HF API (not fal-ai)
                model="artificialguybr/ColoringBookRedmond-V2",
                supports_vectorization=False,
            ),
        }

    def get_cover_model(self) -> ModelMapping:
        """Get model for cover generation."""
        return self._mappings.get("cover", self._mappings["cover"])

    def get_page_model(self) -> ModelMapping:
        """Get model for content page generation."""
        return self._mappings.get("coloring_page", self._mappings["coloring_page"])
