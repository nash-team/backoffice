"""
E2E tests for coloring book UI - no real API calls.

These tests verify the UI behavior without actually calling external APIs.
Fast and reliable for testing the frontend workflow.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_open_modal_and_verify_fields(page: Page, server_url: str):
    """Test that clicking 'Nouvel Ebook' opens modal with all required fields."""

    # Navigate to dashboard
    page.goto(f"{server_url}/")
    page.wait_for_load_state("networkidle")

    # Verify dashboard loaded
    expect(page.locator("h1:has-text('Dashboard')")).to_be_visible()

    # Click "Nouvel Ebook" button
    new_ebook_btn = page.locator('[data-testid="new-ebook-btn"]')
    expect(new_ebook_btn).to_be_visible()
    new_ebook_btn.click()

    # Verify modal opened
    modal = page.locator('[data-testid="ebook-modal"]')
    expect(modal).to_be_visible()

    # Verify form loaded via HTMX
    form = page.locator('[data-testid="ebook-form"]')
    expect(form).to_be_visible(timeout=5000)

    # Verify all form fields are present
    expect(page.locator('[data-testid="theme-select"]')).to_be_visible()
    expect(page.locator('[data-testid="audience-select"]')).to_be_visible()
    expect(page.locator('[data-testid="pages-input"]')).to_be_visible()
    expect(page.locator('[data-testid="create-btn"]')).to_be_visible()
    expect(page.locator('[data-testid="cancel-btn"]')).to_be_visible()

    # Verify theme options are loaded
    theme_select = page.locator('[data-testid="theme-select"]')
    theme_options = theme_select.locator("option")
    expect(theme_options).to_have_count(4)  # Placeholder + 3 themes

    # Verify audience options are loaded
    audience_select = page.locator('[data-testid="audience-select"]')
    audience_options = audience_select.locator("option")
    expect(audience_options).to_have_count(4)  # Placeholder + 3 age groups


@pytest.mark.e2e
def test_form_fields_can_be_filled(page: Page, server_url: str):
    """Test that all form fields can be filled with valid values."""

    # Navigate and open modal
    page.goto(f"{server_url}/")
    page.wait_for_load_state("networkidle")

    new_ebook_btn = page.locator('[data-testid="new-ebook-btn"]')
    new_ebook_btn.click()

    form = page.locator('[data-testid="ebook-form"]')
    expect(form).to_be_visible(timeout=5000)

    # Fill theme
    theme_select = page.locator('[data-testid="theme-select"]')
    theme_select.select_option("dinosaurs")
    expect(theme_select).to_have_value("dinosaurs")

    # Fill audience
    audience_select = page.locator('[data-testid="audience-select"]')
    audience_select.select_option("6-8")
    expect(audience_select).to_have_value("6-8")

    # Fill pages
    pages_input = page.locator('[data-testid="pages-input"]')
    pages_input.fill("10")
    expect(pages_input).to_have_value("10")

    # Optional title field
    title_input = page.locator("#title")
    if title_input.is_visible():
        title_input.fill("Mon livre de test")
        expect(title_input).to_have_value("Mon livre de test")

    # Button should be enabled with valid data
    create_btn = page.locator('[data-testid="create-btn"]')
    expect(create_btn).to_be_enabled()


@pytest.mark.e2e
def test_cancel_button_closes_modal(page: Page, server_url: str):
    """Test that cancel button closes the modal without submitting."""

    # Navigate and open modal
    page.goto(f"{server_url}/")
    page.wait_for_load_state("networkidle")

    new_ebook_btn = page.locator('[data-testid="new-ebook-btn"]')
    new_ebook_btn.click()

    modal = page.locator('[data-testid="ebook-modal"]')
    expect(modal).to_be_visible()

    # Fill some data
    form = page.locator('[data-testid="ebook-form"]')
    expect(form).to_be_visible(timeout=5000)

    theme_select = page.locator('[data-testid="theme-select"]')
    theme_select.select_option("pirates")

    # Click cancel
    cancel_btn = page.locator('[data-testid="cancel-btn"]')
    expect(cancel_btn).to_be_visible()
    cancel_btn.click()

    # Modal should close
    expect(modal).not_to_be_visible(timeout=5000)

    # Should still be on dashboard
    expect(page.locator("h1:has-text('Dashboard')")).to_be_visible()
