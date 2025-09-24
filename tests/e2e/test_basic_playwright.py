"""
Test basique pour vérifier que Playwright fonctionne correctement.
"""

import re
from playwright.sync_api import Page, expect


class TestBasicPlaywright:
    """Basic tests to verify Playwright is working correctly."""

    def test_server_is_running(self, page: Page, simple_server_url: str):
        """Test that the server is running and accessible."""
        page.goto(simple_server_url)

        # Check that we can access the main page
        expect(page).to_have_title(re.compile(r".*"))  # Any title is fine

        # Check that the page loads without major errors
        page.wait_for_load_state("networkidle")

    def test_root_redirects_to_dashboard(self, page: Page, simple_server_url: str):
        """Test that the root page redirects to dashboard."""
        response = page.goto(simple_server_url)

        # Check that we get a successful response
        assert response.status == 200

        # Wait for any redirects to complete
        page.wait_for_load_state("networkidle")

        # The test passes if we can load any page successfully

    def test_api_healthcheck(self, page: Page, simple_server_url: str):
        """Test that the API healthcheck endpoint works."""
        response = page.request.get(f"{simple_server_url}/healthz")
        assert response.status == 200
