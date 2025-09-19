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


templates.env.filters["date"] = format_date
