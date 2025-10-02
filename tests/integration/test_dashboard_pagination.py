import pytest
from datetime import datetime, UTC

from backoffice.domain.entities.ebook import EbookStatus
from backoffice.infrastructure.models.ebook_model import EbookModel


class TestDashboardPagination:
    """Integration tests for dashboard pagination functionality"""

    @pytest.fixture
    def sample_ebooks(self, test_db_session):
        """Create sample ebooks for testing pagination"""
        # Create 20 test ebooks to verify pagination works with multiple pages
        ebooks = []
        for i in range(20):
            ebook = EbookModel(
                title=f"Test Ebook {i+1}",
                author=f"Test Author {i+1}",
                status=EbookStatus.DRAFT.value if i % 2 == 0 else EbookStatus.APPROVED.value,
                created_at=datetime.now(UTC),
            )
            test_db_session.add(ebook)
            ebooks.append(ebook)

        test_db_session.commit()
        return ebooks

    def test_get_ebooks_with_default_pagination(self, test_client, sample_ebooks):
        """Test that default pagination parameters work"""
        response = test_client.get("/api/dashboard/ebooks")

        assert response.status_code == 200
        assert "pagination" in response.context
        pagination = response.context["pagination"]

        # Verify default pagination values
        assert pagination["current_page"] == 1
        assert pagination["page_size"] == 15

    def test_get_ebooks_with_custom_page_size(self, test_client):
        """Test pagination with custom page size"""
        response = test_client.get("/api/dashboard/ebooks?page=1&size=5")

        assert response.status_code == 200
        pagination = response.context["pagination"]
        assert pagination["page_size"] == 5

    def test_get_ebooks_with_specific_page(self, test_client):
        """Test requesting a specific page"""
        response = test_client.get("/api/dashboard/ebooks?page=2&size=5")

        assert response.status_code == 200
        pagination = response.context["pagination"]
        assert pagination["current_page"] == 2

    def test_get_ebooks_with_invalid_page_number(self, test_client):
        """Test handling of invalid page numbers"""
        response = test_client.get("/api/dashboard/ebooks?page=0&size=5")

        assert response.status_code == 400
        assert "Invalid pagination parameters" in response.text

    def test_get_ebooks_with_invalid_page_size(self, test_client):
        """Test handling of invalid page sizes"""
        response = test_client.get("/api/dashboard/ebooks?page=1&size=101")

        assert response.status_code == 400
        assert "Invalid pagination parameters" in response.text

    def test_get_ebooks_with_negative_page(self, test_client):
        """Test handling of negative page numbers"""
        response = test_client.get("/api/dashboard/ebooks?page=-1&size=5")

        assert response.status_code == 400
        assert "Invalid pagination parameters" in response.text

    def test_get_ebooks_with_zero_page_size(self, test_client):
        """Test handling of zero page size"""
        response = test_client.get("/api/dashboard/ebooks?page=1&size=0")

        assert response.status_code == 400
        assert "Invalid pagination parameters" in response.text

    def test_get_ebooks_pagination_with_status_filter(self, test_client):
        """Test that pagination works with status filtering"""
        response = test_client.get("/api/dashboard/ebooks?status=pending&page=1&size=5")

        assert response.status_code == 200
        assert "current_status" in response.context
        assert response.context["current_status"] == "pending"

    def test_get_ebooks_pagination_metadata_structure(self, test_client):
        """Test that pagination metadata has correct structure"""
        response = test_client.get("/api/dashboard/ebooks?page=1&size=10")

        assert response.status_code == 200
        pagination = response.context["pagination"]

        # Verify all required pagination fields are present
        required_fields = [
            "current_page",
            "total_pages",
            "total_count",
            "has_next",
            "has_previous",
            "next_page",
            "previous_page",
            "start_item",
            "end_item",
            "page_size",
        ]

        for field in required_fields:
            assert field in pagination, f"Missing pagination field: {field}"

    def test_pagination_template_includes_pagination_component(self, test_client):
        """Test that the ebooks table template includes pagination when needed"""
        response = test_client.get("/api/dashboard/ebooks")

        assert response.status_code == 200
        # Check that pagination component is included when there's pagination data
        if response.context.get("pagination"):
            assert "pagination" in response.text.lower()

    def test_pagination_preserves_status_filter_in_urls(self, test_client):
        """Test that pagination URLs preserve status filter parameters"""
        response = test_client.get("/api/dashboard/ebooks?status=validated&page=1&size=5")

        assert response.status_code == 200
        # Check that pagination links include the status parameter
        if response.context.get("pagination", {}).get("total_pages", 0) > 1:
            assert "status=validated" in response.text

    def test_pagination_handles_large_page_numbers_gracefully(self, test_client):
        """Test that very large page numbers are handled gracefully"""
        response = test_client.get("/api/dashboard/ebooks?page=9999&size=5")

        # Should still return 200 but with appropriate pagination data
        assert response.status_code == 200
        pagination = response.context["pagination"]

        # Either should be on a valid page or show empty results
        assert pagination["current_page"] == 9999
        assert isinstance(pagination["total_pages"], int)

    def test_pagination_response_format_for_htmx(self, test_client):
        """Test that pagination responses are properly formatted for HTMX"""
        headers = {"HX-Request": "true"}
        response = test_client.get("/api/dashboard/ebooks?page=1&size=5", headers=headers)

        assert response.status_code == 200
        # Response should contain both table and pagination elements
        assert "<table" in response.text
        assert "ebooks" in response.context

    def test_pagination_with_boundary_conditions(self, test_client):
        """Test pagination with boundary conditions"""
        # Test maximum allowed page size
        response = test_client.get("/api/dashboard/ebooks?page=1&size=100")
        assert response.status_code == 200

        # Test minimum page size
        response = test_client.get("/api/dashboard/ebooks?page=1&size=1")
        assert response.status_code == 200
