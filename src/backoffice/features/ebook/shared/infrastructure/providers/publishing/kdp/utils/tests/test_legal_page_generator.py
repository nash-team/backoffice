"""Unit tests for legal page generator."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.legal_page_generator import (
    _build_legal_lines,
    generate_legal_page,
)

FONT_DIR = Path(__file__).resolve().parents[9] / "config" / "branding" / "fonts"

LEGAL_CONFIG = {
    "copyright": {
        "year": 2026,
        "author": "C. Waterton",
        "rights": "Tous droits réservés",
    },
    "publisher": {
        "name": "Éditions Darkwaters",
        "address": "6 Rue des Écoles, 63720 Chavaroux, France",
    },
    "printing": {"country": "France"},
    "legal_deposit": "mars 2026",
}

PAGE_W = 2476  # 8" + 2*0.125" bleed @ 300 DPI
PAGE_H = 3076  # 10" + 2*0.125" bleed @ 300 DPI


class TestGenerateLegalPage:
    def test_returns_valid_png_with_correct_dimensions(self) -> None:
        result = generate_legal_page(
            title="Coloro Dino",
            isbn="9781234567897",
            legal_config=LEGAL_CONFIG,
            page_width_px=PAGE_W,
            page_height_px=PAGE_H,
            font_dir=FONT_DIR,
        )

        img = Image.open(BytesIO(result))
        assert img.format == "PNG"
        assert img.size == (PAGE_W, PAGE_H)
        assert img.mode == "RGB"

    def test_returns_valid_png_without_isbn(self) -> None:
        result = generate_legal_page(
            title="Coloro Dino",
            isbn=None,
            legal_config=LEGAL_CONFIG,
            page_width_px=PAGE_W,
            page_height_px=PAGE_H,
            font_dir=FONT_DIR,
        )

        img = Image.open(BytesIO(result))
        assert img.format == "PNG"
        assert img.size == (PAGE_W, PAGE_H)

    def test_page_is_mostly_white(self) -> None:
        result = generate_legal_page(
            title="Coloro Dino",
            isbn="9781234567897",
            legal_config=LEGAL_CONFIG,
            page_width_px=PAGE_W,
            page_height_px=PAGE_H,
            font_dir=FONT_DIR,
        )

        img = Image.open(BytesIO(result))
        pixels = list(img.getdata())
        white_count = sum(1 for p in pixels if p == (255, 255, 255))
        white_ratio = white_count / len(pixels)
        # Page should be mostly white (text takes very little space)
        assert white_ratio > 0.95


class TestBuildLegalLines:
    def test_lines_with_isbn(self) -> None:
        lines = _build_legal_lines(LEGAL_CONFIG, isbn="9781234567897")

        assert "© 2026 C. Waterton. Tous droits réservés." in lines
        assert "Édité par Éditions Darkwaters" in lines
        assert "6 Rue des Écoles, 63720 Chavaroux, France" in lines
        assert "ISBN 9781234567897" in lines
        assert "Imprimé en France" in lines
        assert "Dépôt légal : mars 2026" in lines

    def test_lines_without_isbn(self) -> None:
        lines = _build_legal_lines(LEGAL_CONFIG, isbn=None)

        isbn_lines = [line for line in lines if "ISBN" in line]
        assert len(isbn_lines) == 0

    def test_lines_order(self) -> None:
        lines = _build_legal_lines(LEGAL_CONFIG, isbn="9781234567897")

        # Copyright should come before publisher
        copyright_idx = next(i for i, l in enumerate(lines) if "©" in l)
        publisher_idx = next(i for i, l in enumerate(lines) if "Édité" in l)
        isbn_idx = next(i for i, l in enumerate(lines) if "ISBN" in l)
        printing_idx = next(i for i, l in enumerate(lines) if "Imprimé" in l)

        assert copyright_idx < publisher_idx < isbn_idx < printing_idx
