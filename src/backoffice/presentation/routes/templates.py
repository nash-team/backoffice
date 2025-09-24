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


# Configuration des statuts ebook
EBOOK_STATUS_CONFIG = {
    "DRAFT": {"label": "Brouillon", "css_class": "bg-secondary"},
    "PENDING": {"label": "En attente", "css_class": "bg-warning text-dark"},
    "APPROVED": {"label": "Approuvé", "css_class": "bg-success"},
    "REJECTED": {"label": "Rejeté", "css_class": "bg-danger"},
}


def format_ebook_status_label(status_value):
    """Retourne le label traduit du statut."""
    return EBOOK_STATUS_CONFIG.get(status_value, {}).get("label", status_value)


def format_ebook_status_class(status_value):
    """Retourne la classe CSS pour le statut."""
    return EBOOK_STATUS_CONFIG.get(status_value, {}).get("css_class", "bg-secondary")


# Enregistrement des filtres
templates.env.filters["date"] = format_date
templates.env.filters["ebook_status_label"] = format_ebook_status_label
templates.env.filters["ebook_status_class"] = format_ebook_status_class
