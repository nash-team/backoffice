"""Configuration loader for YAML configs.

Loads configuration files from the config/ directory at project root.
"""

from pathlib import Path
from typing import Any, cast

import yaml


class ConfigLoader:
    """Loads and caches YAML configuration files."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize config loader.

        Args:
            config_dir: Path to config directory (defaults to project_root/config)
        """
        if config_dir is None:
            # Find project root (where config/ directory AND src/ directory live)
            current = Path(__file__).resolve()
            while current.parent != current:
                # Check for project root markers
                config_path = current / "config"
                src_path = current / "src"
                if config_path.exists() and src_path.exists():
                    config_dir = config_path
                    break
                current = current.parent

        if config_dir is None or not config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")

        self.config_dir = config_dir
        self._cache: dict[str, dict[str, Any]] = {}

    def _load_yaml(self, relative_path: str) -> dict[str, Any]:
        """Load and cache a YAML file.

        Args:
            relative_path: Path relative to config_dir

        Returns:
            Parsed YAML content

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        # Check cache first
        if relative_path in self._cache:
            return self._cache[relative_path]

        full_path = self.config_dir / relative_path

        if not full_path.exists():
            raise FileNotFoundError(f"Config file not found: {full_path}")

        with open(full_path, encoding="utf-8") as f:
            result = cast(dict[str, Any], yaml.safe_load(f))
            self._cache[relative_path] = result
            return result

    # KDP configurations
    def load_kdp_specifications(self) -> dict[str, Any]:
        """Load KDP specifications (trim sizes, bleed, paper types, etc.)."""
        return self._load_yaml("kdp/specifications.yaml")

    def get_kdp_trim_size(self, format_name: str = "square_format") -> tuple[float, float]:
        """Get KDP trim size for a format.

        Args:
            format_name: Format identifier (default: square_format = 8.5x8.5)

        Returns:
            (width, height) in inches
        """
        specs = self.load_kdp_specifications()
        size = specs["formats"][format_name]["trim_size_inches"]
        return (size["width"], size["height"])

    def get_kdp_bleed(self, format_name: str = "square_format") -> float:
        """Get KDP bleed size in inches."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["formats"][format_name]["bleed_inches"])

    def get_kdp_dpi(self, format_name: str = "square_format") -> int:
        """Get KDP DPI requirement."""
        specs = self.load_kdp_specifications()
        return cast(int, specs["formats"][format_name]["dpi"])

    def get_spine_formula(self, paper_type: str) -> float:
        """Get spine width formula (inches per page) for a paper type."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["paper_types"][paper_type]["spine_formula"])

    def get_paper_type_limits(self, paper_type: str) -> dict[str, int]:
        """Get page count limits for a paper type.

        Returns:
            {"min_pages": int, "max_pages": int}
        """
        specs = self.load_kdp_specifications()
        pt = specs["paper_types"][paper_type]
        return {"min_pages": pt["min_pages"], "max_pages": pt["max_pages"]}

    def get_spine_min_width(self) -> float:
        """Get minimum spine width in inches."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["spine"]["min_width_inches"])

    def get_spine_recommended_width(self) -> float:
        """Get recommended spine width in inches."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["spine"]["recommended_width_inches"])

    def get_color_profiles(self) -> dict[str, str]:
        """Get ICC color profiles (RGB/CMYK).

        Returns:
            {"rgb": "profile.icc", "cmyk": "profile.icc"}
        """
        specs = self.load_kdp_specifications()
        return {
            "rgb": specs["color_profiles"]["rgb"]["profile"],
            "cmyk": specs["color_profiles"]["cmyk"]["profile"],
        }

    # New methods for enhanced config

    def get_valid_paper_types(self) -> list[str]:
        """Get list of valid paper types."""
        specs = self.load_kdp_specifications()
        return list(specs["paper_types"].keys())

    def get_valid_cover_finishes(self) -> list[str]:
        """Get list of valid cover finishes."""
        specs = self.load_kdp_specifications()
        return list(specs["cover"]["finish_types"].keys())

    def get_valid_formats(self) -> list[str]:
        """Get list of valid book formats."""
        specs = self.load_kdp_specifications()
        return list(specs["formats"].keys())

    def get_defaults(self) -> dict[str, Any]:
        """Get ColorDream defaults.

        Returns:
            {
                "format": str,
                "paper_type": str,
                "cover_finish": str,
                "include_barcode": bool
            }
        """
        specs = self.load_kdp_specifications()
        return cast(dict[str, Any], specs["defaults"])

    def get_default_paper_type(self) -> str:
        """Get default paper type."""
        return cast(str, self.get_defaults()["paper_type"])

    def get_default_cover_finish(self) -> str:
        """Get default cover finish."""
        return cast(str, self.get_defaults()["cover_finish"])

    def get_default_kdp_format(self) -> str:
        """Get default KDP format."""
        return cast(str, self.get_defaults()["format"])

    def get_default_include_barcode(self) -> bool:
        """Get default include_barcode setting."""
        return cast(bool, self.get_defaults()["include_barcode"])

    def get_paper_type_display_name(self, paper_type: str) -> str:
        """Get display name for a paper type."""
        specs = self.load_kdp_specifications()
        return cast(str, specs["paper_types"][paper_type]["display_name"])

    def get_cover_finish_cost_factor(self, finish: str) -> float:
        """Get cost factor for a cover finish."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["cover"]["finish_types"][finish]["cost_factor"])

    def get_paper_type_cost_factor(self, paper_type: str) -> float:
        """Get cost factor for a paper type."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["paper_types"][paper_type]["cost_factor"])

    def get_export_settings(self) -> dict[str, Any]:
        """Get PDF export settings.

        Returns:
            {
                "pdf_version": str,
                "embed_fonts": bool,
                "compress_images": bool,
                "compression_quality": float
            }
        """
        specs = self.load_kdp_specifications()
        return cast(dict[str, Any], specs["export"])

    def get_validation_rules(self) -> dict[str, Any]:
        """Get validation rules for cover/interior.

        Returns:
            {
                "cover": {...},
                "interior": {...},
                "filenames": {...}
            }
        """
        specs = self.load_kdp_specifications()
        return cast(dict[str, Any], specs["validation"])

    def get_barcode_width(self) -> float:
        """Get KDP barcode width in inches (default: 2.0)."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["cover"]["barcode"]["width_inches"])

    def get_barcode_height(self) -> float:
        """Get KDP barcode height in inches (default: 1.5)."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["cover"]["barcode"]["height_inches"])

    def get_barcode_margin(self) -> float:
        """Get KDP barcode margin in inches (default: 0.25)."""
        specs = self.load_kdp_specifications()
        return cast(float, specs["cover"]["barcode"]["margin_inches"])

    # Business limits
    def load_business_limits(self) -> dict[str, Any]:
        """Load business constraints (pages, formats, etc.)."""
        return self._load_yaml("business/limits.yaml")

    def get_page_limits(self) -> dict[str, int]:
        """Get ebook page limits.

        Returns:
            {"min": int, "max": int}
        """
        limits = self.load_business_limits()
        return cast(dict[str, int], limits["ebook"]["pages"])

    def get_default_format(self) -> str:
        """Get default ebook format."""
        limits = self.load_business_limits()
        return cast(str, limits["ebook"]["formats"]["default"])

    def get_default_engine(self) -> str:
        """Get default PDF engine."""
        limits = self.load_business_limits()
        return cast(str, limits["ebook"]["engines"]["default"])

    def get_cover_min_pixels(self) -> int:
        """Get minimum cover image size in pixels."""
        limits = self.load_business_limits()
        return cast(int, limits["images"]["cover"]["min_pixels"])

    def get_content_min_pixels(self) -> int:
        """Get minimum content image size in pixels."""
        limits = self.load_business_limits()
        return cast(int, limits["images"]["content"]["min_pixels"])

    # Branding & Identity
    def load_brand_identity(self) -> dict[str, Any]:
        """Load brand identity (logo, mascot, colors, etc.)."""
        return self._load_yaml("branding/identity.yaml")

    def get_brand_info(self) -> dict[str, Any]:
        """Get brand information (name, tagline, copyright).

        Returns:
            {
                "name": str,
                "tagline": str,
                "copyright": str,
                "website": str
            }
        """
        identity = self.load_brand_identity()
        return cast(dict[str, Any], identity["brand"])

    def get_logo_config(self) -> dict[str, Any]:
        """Get logo configuration."""
        identity = self.load_brand_identity()
        return cast(dict[str, Any], identity["visual_identity"]["logo"])

    def get_mascot_config(self) -> dict[str, Any]:
        """Get mascot configuration."""
        identity = self.load_brand_identity()
        return cast(dict[str, Any], identity["visual_identity"]["mascot"])

    def get_color_scheme(self) -> dict[str, str]:
        """Get brand color scheme.

        Returns:
            {
                "primary": "#667eea",
                "secondary": "#764ba2",
                "accent": "#FF6B9D",
                ...
            }
        """
        identity = self.load_brand_identity()
        return cast(dict[str, str], identity["visual_identity"]["color_scheme"])

    def get_cover_guidelines(self) -> dict[str, Any]:
        """Get cover element guidelines (always/never include).

        Returns:
            {
                "always_include": [...],
                "optional": [...],
                "never_include": [...]
            }
        """
        identity = self.load_brand_identity()
        return cast(dict[str, Any], identity["cover_elements"])

    def get_style_guidelines(self) -> dict[str, Any]:
        """Get style guidelines for illustrations."""
        identity = self.load_brand_identity()
        return cast(dict[str, Any], identity["style_guidelines"])

    def load_audiences(self) -> dict[str, Any]:
        """Load target audiences configuration."""
        return self._load_yaml("branding/audiences.yaml")

    def get_audience_config(self, audience_id: str) -> dict[str, Any]:
        """Get configuration for a specific audience.

        Args:
            audience_id: Audience ID (e.g., "children", "adults")

        Returns:
            Audience configuration with style, benefits, etc.
        """
        audiences = self.load_audiences()
        return cast(
            dict[str, Any],
            audiences["audiences"].get(audience_id, audiences["audiences"]["children"]),
        )


# Singleton instance for easy import
_config_loader: ConfigLoader | None = None


def get_config_loader() -> ConfigLoader:
    """Get or create singleton ConfigLoader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader
