import re
import pytest
from playwright.async_api import expect


@pytest.mark.e2e
class TestEbookStructureCreation:
    """E2E tests for ebook creation with structure control (chapters/pages)"""

    async def test_story_ebook_with_chapters(self, page, live_server_url):
        """Test creating a story ebook with specific number of chapters"""
        # Navigate to dashboard
        await page.goto(f"{live_server_url}/dashboard")

        # Open ebook creation modal
        await page.click('[data-testid="create-ebook-btn"]')
        await expect(page.locator('[data-testid="ebook-form"]')).to_be_visible()

        # Select story type
        await page.click('[data-testid="ebook-type-card-story"]')
        await expect(page.locator('[data-testid="ebook-type-card-story"]')).to_have_class(
            re.compile(r".*selected.*")
        )

        # Wait for themes to load and select first theme
        await expect(page.locator(".theme-card")).to_be_visible()
        await page.click(".theme-card")

        # Fill prompt
        prompt_text = "Une histoire fantastique avec des dragons et des princesses"
        await page.fill('[data-testid="prompt-textarea"]', prompt_text)

        # Set number of chapters
        await expect(page.locator('[data-testid="chapters-input"]')).to_be_visible()
        await page.fill('[data-testid="chapters-input"]', "7")

        # Verify pages input is not visible for story type
        await expect(page.locator('[data-testid="pages-input"]')).not_to_be_visible()

        # Submit form
        await page.click('[data-testid="create-btn"]')

        # Verify ebook was created and appears in the list
        await expect(page.locator('[data-testid="ebook-title"]').first).to_be_visible(timeout=30000)

        # Verify status shows "En attente" (pending)
        await expect(page.locator(".badge-warning").first).to_be_visible()

    async def test_coloring_ebook_with_pages(self, page, live_server_url):
        """Test creating a coloring ebook with specific number of pages"""
        # Navigate to dashboard
        await page.goto(f"{live_server_url}/dashboard")

        # Open ebook creation modal
        await page.click('[data-testid="create-ebook-btn"]')
        await expect(page.locator('[data-testid="ebook-form"]')).to_be_visible()

        # Select coloring type
        await page.click('[data-testid="ebook-type-card-coloring"]')
        await expect(page.locator('[data-testid="ebook-type-card-coloring"]')).to_have_class(
            re.compile(r".*selected.*")
        )

        # Wait for themes to load and select first theme
        await expect(page.locator(".theme-card")).to_be_visible()
        await page.click(".theme-card")

        # Fill prompt
        prompt_text = "Dessins d'animaux de la ferme à colorier pour enfants"
        await page.fill('[data-testid="prompt-textarea"]', prompt_text)

        # Set number of pages
        await expect(page.locator('[data-testid="pages-input"]')).to_be_visible()
        await page.fill('[data-testid="pages-input"]', "12")

        # Verify chapters input is not visible for coloring type
        await expect(page.locator('[data-testid="chapters-input"]')).not_to_be_visible()

        # Submit form
        await page.click('[data-testid="create-btn"]')

        # Verify ebook was created and appears in the list
        await expect(page.locator('[data-testid="ebook-title"]').first).to_be_visible(timeout=30000)

        # Verify status shows "En attente" (pending)
        await expect(page.locator(".badge-warning").first).to_be_visible()

    async def test_mixed_ebook_with_chapters(self, page, live_server_url):
        """Test creating a mixed ebook with chapters (should show chapters input)"""
        # Navigate to dashboard
        await page.goto(f"{live_server_url}/dashboard")

        # Open ebook creation modal
        await page.click('[data-testid="create-ebook-btn"]')
        await expect(page.locator('[data-testid="ebook-form"]')).to_be_visible()

        # Select mixed type
        await page.click('[data-testid="ebook-type-card-mixed"]')
        await expect(page.locator('[data-testid="ebook-type-card-mixed"]')).to_have_class(
            re.compile(r".*selected.*")
        )

        # Wait for themes to load and select first theme
        await expect(page.locator(".theme-card")).to_be_visible()
        await page.click(".theme-card")

        # Fill prompt
        prompt_text = "Histoire avec des aventures et des pages de coloriage"
        await page.fill('[data-testid="prompt-textarea"]', prompt_text)

        # Set number of chapters (mixed type should show chapters input)
        await expect(page.locator('[data-testid="chapters-input"]')).to_be_visible()
        await page.fill('[data-testid="chapters-input"]', "4")

        # Verify pages input is not visible for mixed type (uses chapters)
        await expect(page.locator('[data-testid="pages-input"]')).not_to_be_visible()

        # Submit form
        await page.click('[data-testid="create-btn"]')

        # Verify ebook was created and appears in the list
        await expect(page.locator('[data-testid="ebook-title"]').first).to_be_visible(timeout=30000)

    async def test_form_validation_chapters_boundary(self, page, live_server_url):
        """Test form validation for chapters at boundary values"""
        # Navigate to dashboard
        await page.goto(f"{live_server_url}/dashboard")

        # Open ebook creation modal
        await page.click('[data-testid="create-ebook-btn"]')
        await expect(page.locator('[data-testid="ebook-form"]')).to_be_visible()

        # Select story type
        await page.click('[data-testid="ebook-type-card-story"]')

        # Try invalid value (too low)
        await page.fill('[data-testid="chapters-input"]', "0")
        # Browser validation should prevent form submission
        create_btn = page.locator('[data-testid="create-btn"]')
        await expect(create_btn).not_to_be_enabled()

        # Try invalid value (too high)
        await page.fill('[data-testid="chapters-input"]', "16")
        # Browser validation should prevent form submission
        await expect(create_btn).not_to_be_enabled()

        # Try valid boundary values
        await page.fill('[data-testid="chapters-input"]', "1")
        await page.fill('[data-testid="chapters-input"]', "15")

    async def test_form_validation_pages_boundary(self, page, live_server_url):
        """Test form validation for pages at boundary values"""
        # Navigate to dashboard
        await page.goto(f"{live_server_url}/dashboard")

        # Open ebook creation modal
        await page.click('[data-testid="create-ebook-btn"]')
        await expect(page.locator('[data-testid="ebook-form"]')).to_be_visible()

        # Select coloring type
        await page.click('[data-testid="ebook-type-card-coloring"]')

        # Try invalid value (too low)
        await page.fill('[data-testid="pages-input"]', "0")
        # Browser validation should prevent form submission
        create_btn = page.locator('[data-testid="create-btn"]')
        await expect(create_btn).not_to_be_enabled()

        # Try invalid value (too high)
        await page.fill('[data-testid="pages-input"]', "31")
        # Browser validation should prevent form submission
        await expect(create_btn).not_to_be_enabled()

        # Try valid boundary values
        await page.fill('[data-testid="pages-input"]', "1")
        await page.fill('[data-testid="pages-input"]', "30")

    async def test_input_visibility_toggle(self, page, live_server_url):
        """Test that the correct input appears based on ebook type selection"""
        # Navigate to dashboard
        await page.goto(f"{live_server_url}/dashboard")

        # Open ebook creation modal
        await page.click('[data-testid="create-ebook-btn"]')
        await expect(page.locator('[data-testid="ebook-form"]')).to_be_visible()

        # Initially, no structure inputs should be visible
        await expect(page.locator('[data-testid="chapters-input"]')).not_to_be_visible()
        await expect(page.locator('[data-testid="pages-input"]')).not_to_be_visible()

        # Select story type - chapters input should appear
        await page.click('[data-testid="ebook-type-card-story"]')
        await expect(page.locator('[data-testid="chapters-input"]')).to_be_visible()
        await expect(page.locator('[data-testid="pages-input"]')).not_to_be_visible()

        # Select coloring type - pages input should appear, chapters should hide
        await page.click('[data-testid="ebook-type-card-coloring"]')
        await expect(page.locator('[data-testid="pages-input"]')).to_be_visible()
        await expect(page.locator('[data-testid="chapters-input"]')).not_to_be_visible()

        # Select mixed type - chapters input should appear, pages should hide
        await page.click('[data-testid="ebook-type-card-mixed"]')
        await expect(page.locator('[data-testid="chapters-input"]')).to_be_visible()
        await expect(page.locator('[data-testid="pages-input"]')).not_to_be_visible()

    async def test_default_values(self, page, live_server_url):
        """Test that default values are set correctly for structure inputs"""
        # Navigate to dashboard
        await page.goto(f"{live_server_url}/dashboard")

        # Open ebook creation modal
        await page.click('[data-testid="create-ebook-btn"]')
        await expect(page.locator('[data-testid="ebook-form"]')).to_be_visible()

        # Select story type and verify default chapters value
        await page.click('[data-testid="ebook-type-card-story"]')
        chapters_input = page.locator('[data-testid="chapters-input"]')
        await expect(chapters_input).to_have_value("5")

        # Select coloring type and verify default pages value
        await page.click('[data-testid="ebook-type-card-coloring"]')
        pages_input = page.locator('[data-testid="pages-input"]')
        await expect(pages_input).to_have_value("8")
