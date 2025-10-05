import pytest

from backoffice.features.shared.domain.entities.pagination import PaginatedResult, PaginationParams


class TestPaginationParams:
    """Test suite for PaginationParams using London methodology"""

    def test_create_pagination_params_with_valid_values(self):
        # When
        params = PaginationParams(page=2, size=10)

        # Then
        assert params.page == 2
        assert params.size == 10
        assert params.offset == 10

    def test_create_pagination_params_with_defaults(self):
        # When
        params = PaginationParams()

        # Then
        assert params.page == 1
        assert params.size == 15
        assert params.offset == 0

    def test_offset_calculation_for_different_pages(self):
        # Given & When
        page_1 = PaginationParams(page=1, size=10)
        page_2 = PaginationParams(page=2, size=10)
        page_3 = PaginationParams(page=3, size=10)

        # Then
        assert page_1.offset == 0
        assert page_2.offset == 10
        assert page_3.offset == 20

    def test_page_validation_rejects_negative_page(self):
        # When & Then
        with pytest.raises(ValueError, match="Page number must be at least 1"):
            PaginationParams(page=0, size=10)

    def test_page_validation_rejects_zero_page(self):
        # When & Then
        with pytest.raises(ValueError, match="Page number must be at least 1"):
            PaginationParams(page=-1, size=10)

    def test_size_validation_rejects_negative_size(self):
        # When & Then
        with pytest.raises(ValueError, match="Page size must be at least 1"):
            PaginationParams(page=1, size=0)

    def test_size_validation_rejects_zero_size(self):
        # When & Then
        with pytest.raises(ValueError, match="Page size must be at least 1"):
            PaginationParams(page=1, size=-1)

    def test_size_validation_rejects_oversized_page(self):
        # When & Then
        with pytest.raises(ValueError, match="Page size cannot exceed 100"):
            PaginationParams(page=1, size=101)

    def test_size_validation_accepts_maximum_size(self):
        # When
        params = PaginationParams(page=1, size=100)

        # Then
        assert params.size == 100


class TestPaginatedResult:
    """Test suite for PaginatedResult using London methodology"""

    def test_create_paginated_result_with_single_page(self):
        # Given
        items = ["item1", "item2", "item3"]

        # When
        result = PaginatedResult(items=items, total_count=3, page=1, size=10)

        # Then
        assert result.items == items
        assert result.total_count == 3
        assert result.page == 1
        assert result.size == 10
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_previous is False
        assert result.next_page is None
        assert result.previous_page is None
        assert result.start_item == 1
        assert result.end_item == 3

    def test_create_paginated_result_with_multiple_pages_first_page(self):
        # Given
        items = ["item1", "item2", "item3"]

        # When
        result = PaginatedResult(items=items, total_count=25, page=1, size=10)

        # Then
        assert result.total_pages == 3
        assert result.has_next is True
        assert result.has_previous is False
        assert result.next_page == 2
        assert result.previous_page is None
        assert result.start_item == 1
        assert result.end_item == 10

    def test_create_paginated_result_with_multiple_pages_middle_page(self):
        # Given
        items = ["item11", "item12", "item13"]

        # When
        result = PaginatedResult(items=items, total_count=25, page=2, size=10)

        # Then
        assert result.total_pages == 3
        assert result.has_next is True
        assert result.has_previous is True
        assert result.next_page == 3
        assert result.previous_page == 1
        assert result.start_item == 11
        assert result.end_item == 20

    def test_create_paginated_result_with_multiple_pages_last_page(self):
        # Given
        items = ["item21", "item22", "item23", "item24", "item25"]

        # When
        result = PaginatedResult(items=items, total_count=25, page=3, size=10)

        # Then
        assert result.total_pages == 3
        assert result.has_next is False
        assert result.has_previous is True
        assert result.next_page is None
        assert result.previous_page == 2
        assert result.start_item == 21
        assert result.end_item == 25

    def test_create_paginated_result_with_empty_results(self):
        # When
        result = PaginatedResult(items=[], total_count=0, page=1, size=10)

        # Then
        assert result.items == []
        assert result.total_count == 0
        assert result.total_pages == 0
        assert result.has_next is False
        assert result.has_previous is False
        assert result.next_page is None
        assert result.previous_page is None
        assert result.start_item == 0
        assert result.end_item == 0

    def test_total_pages_calculation_with_exact_division(self):
        # When
        result = PaginatedResult(items=[], total_count=20, page=1, size=10)

        # Then
        assert result.total_pages == 2

    def test_total_pages_calculation_with_remainder(self):
        # When
        result = PaginatedResult(items=[], total_count=23, page=1, size=10)

        # Then
        assert result.total_pages == 3

    def test_edge_case_single_item_per_page(self):
        # When
        result = PaginatedResult(items=["item1"], total_count=5, page=1, size=1)

        # Then
        assert result.total_pages == 5
        assert result.has_next is True
        assert result.next_page == 2
        assert result.start_item == 1
        assert result.end_item == 1

    def test_edge_case_large_page_size(self):
        # When
        result = PaginatedResult(items=["item1", "item2"], total_count=2, page=1, size=100)

        # Then
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.start_item == 1
        assert result.end_item == 2
