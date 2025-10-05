"""
Configuration centralisée des templates Jinja2.

Supports multiple template directories:
- features/shared/presentation/templates/ (shared: dashboard.html, login.html)
- features/*/presentation/templates/ (feature-specific templates)
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader

# Configuration des templates avec support multi-directories
# BASE_DIR = features/shared/presentation/routes -> go up to features/shared/presentation
BASE_DIR = Path(__file__).resolve().parent.parent
FEATURES_DIR = BASE_DIR.parent.parent  # Go up to features/

# List of template directories (order matters - first found wins)
template_loaders = [
    FileSystemLoader(str(FEATURES_DIR / "shared" / "presentation" / "templates")),
    FileSystemLoader(str(FEATURES_DIR / "ebook_listing" / "presentation" / "templates")),
    FileSystemLoader(str(FEATURES_DIR / "ebook_creation" / "presentation" / "templates")),
    FileSystemLoader(str(FEATURES_DIR / "ebook_lifecycle" / "presentation" / "templates")),
    FileSystemLoader(str(FEATURES_DIR / "ebook_regeneration" / "presentation" / "templates")),
    FileSystemLoader(str(FEATURES_DIR / "ebook_export" / "presentation" / "templates")),
    FileSystemLoader(str(FEATURES_DIR / "generation_costs" / "presentation" / "templates")),
]

# Create Jinja2Templates with ChoiceLoader (searches directories in order)
templates = Jinja2Templates(directory=str(FEATURES_DIR / "shared" / "presentation" / "templates"))
templates.env.loader = ChoiceLoader(template_loaders)


# Ajout du filtre de date
def format_date(value):
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    return value


# Configuration des statuts ebook avec couleurs améliorées
EBOOK_STATUS_CONFIG = {
    "DRAFT": {"label": "Brouillon", "css_class": "badge-draft", "icon": "fa-edit"},
    "APPROVED": {"label": "Approuvé", "css_class": "badge-approved", "icon": "fa-check-circle"},
    "REJECTED": {"label": "Rejeté", "css_class": "badge-rejected", "icon": "fa-times-circle"},
}


def format_ebook_status_label(status_value):
    """Retourne le label traduit du statut."""
    # Handle both string and Enum values
    if hasattr(status_value, "value"):
        status_value = status_value.value
    return EBOOK_STATUS_CONFIG.get(status_value, {}).get("label", status_value)


def format_ebook_status_class(status_value):
    """Retourne la classe CSS pour le statut."""
    # Handle both string and Enum values
    if hasattr(status_value, "value"):
        status_value = status_value.value
    return EBOOK_STATUS_CONFIG.get(status_value, {}).get("css_class", "bg-secondary")


def format_ebook_status_icon(status_value):
    """Retourne l'icône FontAwesome pour le statut."""
    # Handle both string and Enum values
    if hasattr(status_value, "value"):
        status_value = status_value.value
    return EBOOK_STATUS_CONFIG.get(status_value, {}).get("icon", "fa-question-circle")


def format_currency(value: Decimal | float | None, currency: str = "USD") -> str:
    """Format Decimal as currency (avoid float artifacts).

    Args:
        value: Decimal or float value to format
        currency: Currency code (USD, EUR, etc.)

    Returns:
        Formatted currency string (e.g., "$12.34")
    """
    if value is None:
        return "N/A"

    # Convert float to Decimal to avoid precision issues
    if isinstance(value, float):
        value = Decimal(str(value))

    # Round to cent only at display time (not before)
    value = value.quantize(Decimal("0.01"))

    # Currency symbols
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, "$")

    return f"{symbol}{value:,.2f}"


def number_format(value: int | None) -> str:
    """Format integer with thousand separators.

    Args:
        value: Integer to format

    Returns:
        Formatted number string (e.g., "1,234")
    """
    if value is None:
        return "0"
    return f"{value:,}"


# Enregistrement des filtres
templates.env.filters["date"] = format_date
templates.env.filters["ebook_status_label"] = format_ebook_status_label
templates.env.filters["ebook_status_class"] = format_ebook_status_class
templates.env.filters["ebook_status_icon"] = format_ebook_status_icon
templates.env.filters["format_currency"] = format_currency
templates.env.filters["number_format"] = number_format
