import pytest
from playwright.async_api import Page, expect

from backoffice.domain.entities.ebook import EbookStatus
from tests.e2e.scenarios_helpers import EbookTestHelpers


class TestValidationWorkflow:
    """E2E tests for the ebook validation workflow"""

    @pytest.mark.asyncio
    async def test_complete_validation_workflow(
        self, page: Page, base_url: str, ebook_test_helpers: EbookTestHelpers
    ):
        """Test the complete validation workflow: create -> validate -> approve/reject"""

        # Navigate to dashboard
        await page.goto(f"{base_url}/dashboard")

        # Wait for dashboard to load
        await expect(page.locator('[data-testid="stats-section"]')).to_be_visible()
        await expect(page.locator('[data-testid="ebooks-section"]')).to_be_visible()

        # Create a test ebook first using the helper
        test_ebook = await ebook_test_helpers.create_test_ebook(
            title="Test Validation Ebook", author="Test Author", status=EbookStatus.PENDING
        )

        # Refresh the page to see the new ebook
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Verify the ebook appears in the table with PENDING status
        ebook_row = page.locator(f'[data-testid="ebook-row-{test_ebook.id}"]')
        await expect(ebook_row).to_be_visible()

        # Check status badge shows "En attente"
        status_badge = ebook_row.locator(".badge")
        await expect(status_badge).to_contain_text("En attente")
        await expect(status_badge).to_have_class(pattern="bg-warning")

        # Verify approve and reject buttons are present
        approve_btn = ebook_row.locator(f'[data-testid="approve-btn-{test_ebook.id}"]')
        reject_btn = ebook_row.locator(f'[data-testid="reject-btn-{test_ebook.id}"]')

        await expect(approve_btn).to_be_visible()
        await expect(reject_btn).to_be_visible()

        # Test approve workflow
        await approve_btn.click()
        await page.wait_for_load_state("networkidle")

        # Verify status changed to APPROVED
        await expect(status_badge).to_contain_text("Approuvé")
        await expect(status_badge).to_have_class(pattern="bg-success")

        # Verify only reject button is now available
        await expect(approve_btn).not_to_be_visible()
        await expect(reject_btn).to_be_visible()

        # Test reject workflow (from approved status)
        await reject_btn.click()
        await page.wait_for_load_state("networkidle")

        # Verify status changed to REJECTED
        await expect(status_badge).to_contain_text("Rejeté")
        await expect(status_badge).to_have_class(pattern="bg-danger")

        # Verify only approve button is now available
        await expect(approve_btn).to_be_visible()
        await expect(reject_btn).not_to_be_visible()

    @pytest.mark.asyncio
    async def test_status_filtering_workflow(
        self, page: Page, base_url: str, ebook_test_helpers: EbookTestHelpers
    ):
        """Test filtering ebooks by different status values"""

        # Create test ebooks with different statuses
        draft_ebook = await ebook_test_helpers.create_test_ebook(
            title="Draft Ebook", author="Test Author", status=EbookStatus.DRAFT
        )

        pending_ebook = await ebook_test_helpers.create_test_ebook(
            title="Pending Ebook", author="Test Author", status=EbookStatus.PENDING
        )

        approved_ebook = await ebook_test_helpers.create_test_ebook(
            title="Approved Ebook", author="Test Author", status=EbookStatus.APPROVED
        )

        rejected_ebook = await ebook_test_helpers.create_test_ebook(
            title="Rejected Ebook", author="Test Author", status=EbookStatus.REJECTED
        )

        # Navigate to dashboard
        await page.goto(f"{base_url}/dashboard")
        await page.wait_for_load_state("networkidle")

        # Test "All" filter (default)
        all_btn = page.locator('[data-testid="filter-all-btn"]')
        await expect(all_btn).to_have_class(pattern="active")

        # Should see all 4 ebooks
        await expect(page.locator(f'[data-testid="ebook-row-{draft_ebook.id}"]')).to_be_visible()
        await expect(page.locator(f'[data-testid="ebook-row-{pending_ebook.id}"]')).to_be_visible()
        await expect(page.locator(f'[data-testid="ebook-row-{approved_ebook.id}"]')).to_be_visible()
        await expect(page.locator(f'[data-testid="ebook-row-{rejected_ebook.id}"]')).to_be_visible()

        # Test "Brouillons" filter
        draft_btn = page.locator('[data-testid="filter-draft-btn"]')
        await draft_btn.click()
        await page.wait_for_load_state("networkidle")

        await expect(draft_btn).to_have_class(pattern="active")
        await expect(page.locator(f'[data-testid="ebook-row-{draft_ebook.id}"]')).to_be_visible()
        await expect(
            page.locator(f'[data-testid="ebook-row-{pending_ebook.id}"]')
        ).not_to_be_visible()

        # Test "En attente" filter
        pending_btn = page.locator('[data-testid="filter-pending-btn"]')
        await pending_btn.click()
        await page.wait_for_load_state("networkidle")

        await expect(pending_btn).to_have_class(pattern="active")
        await expect(page.locator(f'[data-testid="ebook-row-{pending_ebook.id}"]')).to_be_visible()
        await expect(
            page.locator(f'[data-testid="ebook-row-{draft_ebook.id}"]')
        ).not_to_be_visible()

        # Test "Approuvés" filter
        approved_btn = page.locator('[data-testid="filter-approved-btn"]')
        await approved_btn.click()
        await page.wait_for_load_state("networkidle")

        await expect(approved_btn).to_have_class(pattern="active")
        await expect(page.locator(f'[data-testid="ebook-row-{approved_ebook.id}"]')).to_be_visible()
        await expect(
            page.locator(f'[data-testid="ebook-row-{pending_ebook.id}"]')
        ).not_to_be_visible()

        # Test "Rejetés" filter
        rejected_btn = page.locator('[data-testid="filter-rejected-btn"]')
        await rejected_btn.click()
        await page.wait_for_load_state("networkidle")

        await expect(rejected_btn).to_have_class(pattern="active")
        await expect(page.locator(f'[data-testid="ebook-row-{rejected_ebook.id}"]')).to_be_visible()
        await expect(
            page.locator(f'[data-testid="ebook-row-{approved_ebook.id}"]')
        ).not_to_be_visible()

    @pytest.mark.asyncio
    async def test_stats_update_after_validation(
        self, page: Page, base_url: str, ebook_test_helpers: EbookTestHelpers
    ):
        """Test that stats are updated correctly after validation actions"""

        # Create a pending ebook
        test_ebook = await ebook_test_helpers.create_test_ebook(
            title="Stats Test Ebook", author="Test Author", status=EbookStatus.PENDING
        )

        # Navigate to dashboard
        await page.goto(f"{base_url}/dashboard")
        await page.wait_for_load_state("networkidle")

        # Get initial stats
        stats_section = page.locator('[data-testid="stats-section"]')
        await expect(stats_section).to_be_visible()

        # Get the pending count
        pending_stat = stats_section.locator('h5:has-text("En attente")').locator("+ p")
        initial_pending_count = await pending_stat.text_content()

        # Approve the ebook
        ebook_row = page.locator(f'[data-testid="ebook-row-{test_ebook.id}"]')
        approve_btn = ebook_row.locator(f'[data-testid="approve-btn-{test_ebook.id}"]')
        await approve_btn.click()
        await page.wait_for_load_state("networkidle")

        # Refresh to see updated stats
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Verify stats are updated
        approved_stat = stats_section.locator('h5:has-text("Approuvés")').locator("+ p")
        await expect(approved_stat).not_to_have_text("0")

        # Verify pending count decreased (if there were others)
        new_pending_count = await pending_stat.text_content()
        assert (
            int(new_pending_count) < int(initial_pending_count)
            if int(initial_pending_count) > 0
            else True
        )

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, page: Page, base_url: str):
        """Test error handling for invalid validation operations"""

        # Navigate to dashboard
        await page.goto(f"{base_url}/dashboard")
        await page.wait_for_load_state("networkidle")

        # Try to approve non-existent ebook by directly calling the API endpoint
        response = await page.request.put(f"{base_url}/api/dashboard/ebooks/99999/approve")
        assert response.status == 400

        # Try to reject non-existent ebook
        response = await page.request.put(f"{base_url}/api/dashboard/ebooks/99999/reject")
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_validation_buttons_visibility_by_status(
        self, page: Page, base_url: str, ebook_test_helpers: EbookTestHelpers
    ):
        """Test that validation buttons are shown/hidden correctly based on status"""

        # Create ebooks with different statuses
        draft_ebook = await ebook_test_helpers.create_test_ebook(
            title="Draft Test", status=EbookStatus.DRAFT
        )

        pending_ebook = await ebook_test_helpers.create_test_ebook(
            title="Pending Test", status=EbookStatus.PENDING
        )

        # Navigate to dashboard
        await page.goto(f"{base_url}/dashboard")
        await page.wait_for_load_state("networkidle")

        # Check DRAFT ebook has no validation buttons
        draft_row = page.locator(f'[data-testid="ebook-row-{draft_ebook.id}"]')
        await expect(
            draft_row.locator(f'[data-testid="approve-btn-{draft_ebook.id}"]')
        ).not_to_be_visible()
        await expect(
            draft_row.locator(f'[data-testid="reject-btn-{draft_ebook.id}"]')
        ).not_to_be_visible()

        # Check PENDING ebook has both buttons
        pending_row = page.locator(f'[data-testid="ebook-row-{pending_ebook.id}"]')
        await expect(
            pending_row.locator(f'[data-testid="approve-btn-{pending_ebook.id}"]')
        ).to_be_visible()
        await expect(
            pending_row.locator(f'[data-testid="reject-btn-{pending_ebook.id}"]')
        ).to_be_visible()
