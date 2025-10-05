"""
E2E Smoke test - Minimal health check to verify app starts.

Complex UI tests are not maintained here - UI evolves too rapidly.
For UI testing, prefer manual testing or dedicated QA environment.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_app_starts_and_responds(page: Page, server_url: str):
    """Test that the app starts and the health check endpoint works."""
    # Navigate to health endpoint
    page.goto(f"{server_url}/healthz")

    # Should see success response
    expect(page.locator("body")).to_contain_text("ok")
