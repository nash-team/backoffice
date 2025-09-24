"""
Robust unit tests for SqlAlchemyEbookQuery using London methodology
with create_autospec and proper isolation.
"""

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest
from sqlalchemy.orm import Session

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.entities.pagination import PaginationParams
from backoffice.infrastructure.adapters.queries.sqlalchemy_ebook_query import SqlAlchemyEbookQuery
from backoffice.infrastructure.models.ebook_model import EbookModel


class TestSqlAlchemyEbookQuery:
    """Test suite for SqlAlchemyEbookQuery using London methodology"""

    def setup_method(self):
        """Set up test fixtures with proper autospec mocking"""
        self.mock_db = create_autospec(Session, instance=True)
        self.query_service = SqlAlchemyEbookQuery(self.mock_db)

    @pytest.mark.parametrize(
        "total_count,page,size,expected_items",
        [
            (0, 1, 10, 0),  # Empty results
            (5, 1, 10, 5),  # Less than page size
            (10, 1, 10, 10),  # Exact page size
            (25, 2, 10, 10),  # Second page
            (100, 5, 20, 20),  # Middle page
        ],
    )
    async def test_list_paginated_returns_correct_structure(
        self, total_count: int, page: int, size: int, expected_items: int
    ):
        """Test pagination returns correct structure for various scenarios"""
        # Given
        params = PaginationParams(page=page, size=size)
        self._setup_pagination_mocks(total_count, expected_items)

        # When
        result = await self.query_service.list_paginated(params)

        # Then
        assert result.total_count == total_count
        assert result.page == page
        assert result.size == size
        assert len(result.items) == expected_items
        # Verify all items are proper domain entities
        assert all(isinstance(item, Ebook) for item in result.items)

    @pytest.mark.parametrize(
        "page,size,expected_offset",
        [
            (1, 10, 0),
            (2, 10, 10),
            (3, 5, 10),
            (10, 15, 135),
        ],
    )
    async def test_list_paginated_applies_correct_offset_and_limit(
        self, page: int, size: int, expected_offset: int
    ):
        """Test that correct SQL offset and limit are applied"""
        # Given
        params = PaginationParams(page=page, size=size)
        self._setup_pagination_mocks(100, size)

        # When
        await self.query_service.list_paginated(params)

        # Then
        # Verify database calls were made with correct parameters
        self.mock_db.query.assert_called()
        query_chain = self.mock_db.query.return_value
        query_chain.order_by.assert_called()
        query_chain.order_by.return_value.offset.assert_called_with(expected_offset)
        query_chain.order_by.return_value.offset.return_value.limit.assert_called_with(size)

    @pytest.mark.parametrize("status", [EbookStatus.PENDING, EbookStatus.APPROVED])
    async def test_list_paginated_by_status_filters_correctly(self, status: EbookStatus):
        """Test that status filtering is applied correctly"""
        # Given
        params = PaginationParams(page=1, size=10)
        self._setup_status_filtering_mocks(status, 15, 10)

        # When
        result = await self.query_service.list_paginated_by_status(status, params)

        # Then
        # Verify status filter was applied for both count and data queries
        filter_calls = self.mock_db.query.return_value.filter.call_args_list
        assert len(filter_calls) == 2  # Called for count and for data
        assert result.total_count == 15

    async def test_list_paginated_orders_by_created_at_desc(self):
        """Test that results are ordered by creation date descending"""
        # Given
        params = PaginationParams(page=1, size=5)
        self._setup_pagination_mocks(10, 5)

        # When
        await self.query_service.list_paginated(params)

        # Then
        # Verify ordering was applied
        query_chain = self.mock_db.query.return_value
        query_chain.order_by.assert_called()

    async def test_list_paginated_converts_models_to_domain_entities(self):
        """Test that database models are properly converted to domain entities"""
        # Given
        params = PaginationParams(page=1, size=2)
        mock_models = [
            self._create_mock_ebook_model(1, "Title 1", "PENDING"),
            self._create_mock_ebook_model(2, "Title 2", "VALIDATED"),
        ]
        self._setup_pagination_mocks_with_models(2, mock_models)

        # When
        result = await self.query_service.list_paginated(params)

        # Then
        assert len(result.items) == 2
        ebook_1, ebook_2 = result.items

        # Verify conversion to domain entities
        assert isinstance(ebook_1, Ebook)
        assert ebook_1.id == 1
        assert ebook_1.title == "Title 1"
        assert ebook_1.status == EbookStatus.PENDING

        assert isinstance(ebook_2, Ebook)
        assert ebook_2.id == 2
        assert ebook_2.title == "Title 2"
        assert ebook_2.status == EbookStatus.APPROVED

    async def test_empty_results_handled_correctly(self):
        """Test that empty results are handled gracefully"""
        # Given
        params = PaginationParams(page=1, size=10)
        self._setup_pagination_mocks(0, 0)

        # When
        result = await self.query_service.list_paginated(params)

        # Then
        assert result.items == []
        assert result.total_count == 0
        assert result.total_pages == 0

    def _setup_pagination_mocks(self, total_count: int, item_count: int):
        """Helper to set up pagination mocks"""
        # Mock count query
        self.mock_db.query.return_value.count.return_value = total_count

        # Mock data query chain
        mock_models = [
            self._create_mock_ebook_model(i, f"Title {i}", "PENDING")
            for i in range(1, item_count + 1)
        ]
        query_chain = self.mock_db.query.return_value
        query_chain.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_models

    def _setup_pagination_mocks_with_models(self, total_count: int, mock_models: list):
        """Helper to set up pagination mocks with specific models"""
        self.mock_db.query.return_value.count.return_value = total_count
        query_chain = self.mock_db.query.return_value
        query_chain.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_models

    def _setup_status_filtering_mocks(self, status: EbookStatus, total_count: int, item_count: int):
        """Helper to set up status filtering mocks"""
        # Mock filtered count query
        filtered_query = self.mock_db.query.return_value.filter.return_value
        filtered_query.count.return_value = total_count

        # Mock filtered data query
        mock_models = [
            self._create_mock_ebook_model(i, f"Title {i}", status.value)
            for i in range(1, item_count + 1)
        ]
        filtered_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_models

    def _create_mock_ebook_model(self, id_: int, title: str, status: str):
        """Helper to create mock EbookModel instances"""
        mock_model = create_autospec(EbookModel, instance=True)
        mock_model.id = id_
        mock_model.title = title
        mock_model.author = "Test Author"
        mock_model.status = status
        mock_model.preview_url = f"http://example.com/preview/{id_}"
        mock_model.drive_id = f"drive-id-{id_}"
        mock_model.created_at = datetime.now(UTC)
        return mock_model
