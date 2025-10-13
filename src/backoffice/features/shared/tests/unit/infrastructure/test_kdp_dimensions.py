"""Unit tests for KDP dimension calculations and validations."""

import pytest

from backoffice.features.ebook.shared.domain.entities.ebook import (
    calculate_spine_width,
    can_have_spine_text,
    inches_to_px,
)
from backoffice.features.ebook.shared.infrastructure.utils.color_utils import TEXT_BLACK_CMYK


def test_spine_width_calculations():
    """Test spine width formulas for different paper types."""
    # Premium color
    assert calculate_spine_width(100, "premium_color") == pytest.approx(0.2347, rel=1e-4)

    # Standard color
    assert calculate_spine_width(100, "standard_color") == pytest.approx(0.2252, rel=1e-4)

    # White paper
    assert calculate_spine_width(100, "white") == pytest.approx(0.2252, rel=1e-4)

    # Cream paper
    assert calculate_spine_width(100, "cream") == pytest.approx(0.25, rel=1e-4)


def test_can_have_spine_text_edge_cases():
    """Test spine text eligibility at boundary conditions."""
    # ✅ 26 pages premium: 26 * 0.002347 = 0.061022" < 0.0625" → NO text
    can_text, reason = can_have_spine_text(26, "premium_color")
    assert not can_text
    assert "trop étroite" in reason

    # 27 pages premium: 27 * 0.002347 = 0.063369" > 0.0625" → OK
    can_text, reason = can_have_spine_text(27, "premium_color")
    assert can_text
    # Borderline warning (< 0.08")
    assert "⚠️" in reason

    # 78 pages cream: 78 * 0.0025 = 0.195" → OK large
    can_text, reason = can_have_spine_text(78, "cream")
    assert can_text
    assert reason == ""  # No warning


def test_dimensions_rounded_to_even():
    """Test that pixel conversions are rounded to even numbers."""
    bleed_px = inches_to_px(0.125)
    assert bleed_px % 2 == 0, f"Bleed should be even: {bleed_px}"

    spine_px = inches_to_px(0.063)
    assert spine_px % 2 == 0, f"Spine should be even: {spine_px}"

    trim_width = inches_to_px(8.0)
    assert trim_width % 2 == 0, f"Trim width should be even: {trim_width}"


def test_text_black_cmyk_value():
    """Test that K 100% is correctly represented in PIL (255, not 100)."""
    assert TEXT_BLACK_CMYK == (0, 0, 0, 255), "K 100% should be (0,0,0,255) in PIL"


def test_inches_to_px_accuracy():
    """Test inches to pixels conversion at 300 DPI."""
    # 1 inch = 300px at 300 DPI
    assert inches_to_px(1.0) == 300

    # 0.125 inch (bleed) = 37.5px → rounded to 38 (even)
    bleed_px = inches_to_px(0.125)
    assert bleed_px == 38, f'0.125" should be 38px (rounded even), got {bleed_px}'

    # 8 inches = 2400px
    assert inches_to_px(8.0) == 2400

    # 10 inches = 3000px
    assert inches_to_px(10.0) == 3000
