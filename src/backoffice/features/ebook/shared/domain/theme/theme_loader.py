import logging
from pathlib import Path

from backoffice.features.ebook.shared.domain.entities.theme_profile import (
    ThemeProfile,
    load_theme_from_yaml,
)

logger = logging.getLogger(__name__)


class ThemeLoader:
    """Service for loading and managing theme configurations"""

    def __init__(self, themes_directory: Path):
        self.themes_directory = themes_directory
        self._theme_cache: dict[str, ThemeProfile] = {}
        self._neutral_theme: ThemeProfile | None = None

    def load_theme(self, theme_id: str) -> ThemeProfile:
        """Load a theme by ID with caching and fallback"""
        # Check cache first
        if theme_id in self._theme_cache:
            logger.debug(f"Theme '{theme_id}' loaded from cache")
            return self._theme_cache[theme_id]

        # Try to load from file
        theme_file = self.themes_directory / f"{theme_id}.yml"

        try:
            if not theme_file.exists():
                logger.warning(f"Theme file not found: {theme_file}")
                return self._get_fallback_theme()

            theme = load_theme_from_yaml(theme_file)

            # Validate theme ID matches filename
            if theme.id != theme_id:
                logger.warning(f"Theme ID mismatch: file '{theme_id}.yml' contains theme '{theme.id}'")
                return self._get_fallback_theme()

            # Cache successful load
            self._theme_cache[theme_id] = theme
            logger.info(f"Theme '{theme_id}' loaded successfully")
            return theme

        except Exception as e:
            logger.error(f"Failed to load theme '{theme_id}': {e}")
            return self._get_fallback_theme()

    def get_available_themes(self) -> list[ThemeProfile]:
        """Get list of all available themes"""
        themes = []

        if not self.themes_directory.exists():
            logger.warning(f"Themes directory does not exist: {self.themes_directory}")
            return [self._get_fallback_theme()]

        for theme_file in self.themes_directory.glob("*.yml"):
            if theme_file.name == "neutral-default.yml":
                continue  # Skip fallback theme from listing

            theme_id = theme_file.stem
            try:
                theme = self.load_theme(theme_id)
                themes.append(theme)
            except Exception as e:
                logger.error(f"Failed to load theme from {theme_file}: {e}")
                continue

        # Sort by label for consistent ordering
        themes.sort(key=lambda t: t.label)

        if not themes:
            logger.warning("No valid themes found, returning fallback only")
            return [self._get_fallback_theme()]

        return themes

    def clear_cache(self) -> None:
        """Clear the theme cache"""
        self._theme_cache.clear()
        self._neutral_theme = None
        logger.info("Theme cache cleared")

    def _get_fallback_theme(self) -> ThemeProfile:
        """Get or create the neutral fallback theme"""
        if self._neutral_theme is not None:
            return self._neutral_theme

        # Try to load neutral-default theme
        neutral_file = self.themes_directory / "neutral-default.yml"

        try:
            if neutral_file.exists():
                self._neutral_theme = load_theme_from_yaml(neutral_file)
                logger.info("Loaded neutral-default theme as fallback")
                return self._neutral_theme
        except Exception as e:
            logger.error(f"Failed to load neutral-default theme: {e}")

        # Create hardcoded fallback if file doesn't exist or fails
        logger.warning("Creating hardcoded neutral fallback theme")
        self._neutral_theme = self._create_hardcoded_fallback()
        return self._neutral_theme

    def _create_hardcoded_fallback(self) -> ThemeProfile:
        """Create a hardcoded neutral theme as last resort"""
        from backoffice.features.ebook.shared.domain.entities.theme_profile import (
            Palette,
            PromptBlocks,
            ThemeProfile,
        )

        return ThemeProfile(
            id="neutral-fallback",
            label="Neutral Theme (Fallback)",
            palette=Palette(
                base=["#ffffff", "#f5f5f5", "#e0e0e0"],
                accents_allowed=["#666666", "#333333"],
                forbidden_keywords=["bright neon", "rainbow gradient"],
            ),
            blocks=PromptBlocks(
                subject="a simple, child-friendly illustration, centered composition",
                environment="clean white background, minimal details",
                tone="calm, neutral, kid-friendly",
                positives=[
                    "clean lines",
                    "simple design",
                    "professional children's book style",
                    "high quality",
                ],
                negatives=[
                    "no text",
                    "no mockup",
                    "no borders",
                    "no complex details",
                    "no dark themes",
                ],
            ),
        )
