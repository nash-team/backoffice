"""
Configuration centralisée des templates Jinja2.
"""

from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

# Configuration des templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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


# Enregistrement des filtres
templates.env.filters["date"] = format_date
templates.env.filters["ebook_status_label"] = format_ebook_status_label
templates.env.filters["ebook_status_class"] = format_ebook_status_class
templates.env.filters["ebook_status_icon"] = format_ebook_status_icon
