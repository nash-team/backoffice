import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateError

logger = logging.getLogger(__name__)


class TemplateLoadingError(Exception):
    """Exception raised when template loading fails"""

    pass


class TemplateRenderingError(Exception):
    """Exception raised when template rendering fails"""

    pass


class CommonTemplateLoader:
    """Common utility for loading and rendering Jinja2 templates"""

    def __init__(self, templates_dir: str | Path):
        """
        Initialize template loader with templates directory

        Args:
            templates_dir: Path to templates directory
        """
        self.templates_dir = Path(templates_dir)
        self._jinja_env: Environment | None = None

    @property
    def jinja_env(self) -> Environment:
        """Lazy-loaded Jinja2 environment with caching"""
        if self._jinja_env is None:
            self._jinja_env = Environment(
                loader=FileSystemLoader(self.templates_dir), autoescape=True
            )
            logger.debug(f"Jinja2 environment initialized with dir: {self.templates_dir}")
        return self._jinja_env

    def load_template(self, template_path: str):
        """
        Load a template by path

        Args:
            template_path: Relative path to template

        Returns:
            Jinja2 Template object

        Raises:
            TemplateLoadingError: If template cannot be loaded
        """
        try:
            template = self.jinja_env.get_template(template_path)
            logger.debug(f"Template loaded successfully: {template_path}")
            return template
        except TemplateError as e:
            logger.error(f"Template loading error for {template_path}: {e}")
            raise TemplateLoadingError(f"Failed to load template {template_path}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error loading template {template_path}: {e}")
            raise TemplateLoadingError(f"Unexpected error loading {template_path}: {e}") from e

    def render_template(self, template_path: str, context: dict[str, Any]) -> str:
        """
        Load and render a template with given context

        Args:
            template_path: Relative path to template
            context: Template context data

        Returns:
            Rendered HTML string

        Raises:
            TemplateRenderingError: If rendering fails
        """
        try:
            template = self.load_template(template_path)
            rendered: str = template.render(context)
            logger.debug(f"Template rendered successfully: {template_path}")
            return rendered
        except TemplateLoadingError:
            # Re-raise template loading errors as-is
            raise
        except TemplateError as e:
            logger.error(f"Template rendering error for {template_path}: {e}")
            raise TemplateRenderingError(f"Rendering failed for {template_path}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected rendering error for {template_path}: {e}")
            raise TemplateRenderingError(
                f"Unexpected rendering error for {template_path}: {e}"
            ) from e

    def template_exists(self, template_path: str) -> bool:
        """
        Check if a template file exists

        Args:
            template_path: Relative path to template

        Returns:
            True if template exists, False otherwise
        """
        full_path = self.templates_dir / template_path
        exists = full_path.exists() and full_path.is_file()
        logger.debug(f"Template existence check for {template_path}: {exists}")
        return exists

    def get_templates_dir(self) -> Path:
        """Get the templates directory path"""
        return self.templates_dir


def create_template_loader(templates_dir: str | Path) -> CommonTemplateLoader:
    """
    Factory function to create a CommonTemplateLoader

    Args:
        templates_dir: Path to templates directory

    Returns:
        Configured CommonTemplateLoader instance
    """
    return CommonTemplateLoader(templates_dir)
