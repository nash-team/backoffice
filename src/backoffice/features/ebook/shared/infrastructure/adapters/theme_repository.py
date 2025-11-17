import logging
from pathlib import Path

from backoffice.features.ebook.shared.domain.entities.theme_profile import ThemeProfile, ThemeProfileModel
from backoffice.features.ebook.shared.domain.theme.theme_loader import ThemeLoader

logger = logging.getLogger(__name__)


class ThemeRepository:
    """Repository adapter for theme management"""

    def __init__(self, themes_directory: Path | None = None):
        if themes_directory is None:
            # Find project root by looking for config/ directory
            current = Path(__file__).resolve()
            while current.parent != current:
                config_dir = current / "config" / "branding" / "themes"
                if config_dir.exists():
                    themes_directory = config_dir
                    break
                current = current.parent

            if themes_directory is None:
                raise FileNotFoundError("Could not find config/branding/themes in project tree")

        self.themes_directory = themes_directory
        self._theme_loader = ThemeLoader(themes_directory)

        logger.info(f"ThemeRepository initialized with themes directory: {themes_directory}")

    def get_theme_by_id(self, theme_id: str) -> ThemeProfile:
        """Get a theme by its ID"""
        logger.debug(f"Retrieving theme: {theme_id}")
        return self._theme_loader.load_theme(theme_id)

    def get_available_themes(self) -> list[ThemeProfile]:
        """Get all available themes"""
        logger.debug("Retrieving all available themes")
        return self._theme_loader.get_available_themes()

    def get_themes_for_ui(self) -> list[dict]:
        """Get themes formatted for UI consumption"""
        themes = self.get_available_themes()
        return [
            {
                "id": theme.id,
                "label": theme.label,
                "description": f"Thème {theme.label.lower()}",
            }
            for theme in themes
        ]

    def clear_cache(self) -> None:
        """Clear the theme cache"""
        logger.info("Clearing theme cache")
        self._theme_loader.clear_cache()

    def validate_theme_id(self, theme_id: str) -> bool:
        """Validate if a theme ID exists and is loadable"""
        try:
            self.get_theme_by_id(theme_id)
            return True
        except Exception as e:
            logger.warning(f"Theme validation failed for '{theme_id}': {e}")
            return False

    def get_theme_version(self, theme_id: str) -> str:
        """Get theme version/timestamp for caching purposes"""
        theme_file = self.themes_directory / f"{theme_id}.yml"
        if theme_file.exists():
            # Use file modification time as version
            mtime = theme_file.stat().st_mtime
            return str(int(mtime))
        return "unknown"

    def is_available(self) -> bool:
        """Check if the theme repository is available and functional"""
        try:
            themes = self.get_available_themes()
            return len(themes) > 0
        except Exception as e:
            logger.error(f"Theme repository availability check failed: {e}")
            return False
