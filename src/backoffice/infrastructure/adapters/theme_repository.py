import logging
from pathlib import Path

from backoffice.domain.entities.theme_profile import ThemeProfile
from backoffice.domain.services.theme_loader import ThemeLoader

logger = logging.getLogger(__name__)


class ThemeRepository:
    """Repository adapter for theme management"""

    def __init__(self, themes_directory: Path | None = None):
        if themes_directory is None:
            # Default to themes directory at project root
            project_root = Path(__file__).parent.parent.parent.parent.parent
            themes_directory = project_root / "themes"

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
