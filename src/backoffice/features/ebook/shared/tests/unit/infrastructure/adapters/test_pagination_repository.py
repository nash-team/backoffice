from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.entities.pagination import PaginatedResult, PaginationParams
from backoffice.features.ebook.shared.infrastructure.models.ebook_model import EbookModel
from backoffice.features.ebook.shared.infrastructure.repositories.ebook_repository import (
    SqlAlchemyEbookRepository,
)


class TestSqlAlchemyEbookRepositoryPagination:
    """Test suite for pagination in SqlAlchemyEbookRepository using London methodology"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.repository = SqlAlchemyEbookRepository(self.mock_db)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_paginated_returns_correct_structure(self):
        # Given
        params = PaginationParams(page=1, size=5)

        # Mock database responses
        self.mock_db.query.return_value.count.return_value = 15
        mock_query = self.mock_db.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            self._create_mock_ebook_model(1, "Title 1"),
            self._create_mock_ebook_model(2, "Title 2"),
        ]

        # When
        result = await self.repository.get_paginated(params)

        # Then
        assert isinstance(result, PaginatedResult)
        assert len(result.items) == 2
        assert result.total_count == 15
        assert result.page == 1
        assert result.size == 5
        assert all(isinstance(item, Ebook) for item in result.items)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_paginated_applies_correct_offset_and_limit(self):
        # Given
        params = PaginationParams(page=3, size=10)

        # Mock database responses
        self.mock_db.query.return_value.count.return_value = 50
        mock_query = self.mock_db.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        # When
        await self.repository.get_paginated(params)

        # Then
        # Verify correct SQL parameters were used
        mock_query.order_by.assert_called_once()
        mock_query.order_by.return_value.offset.assert_called_once_with(20)  # (3-1) * 10
        mock_query.order_by.return_value.offset.return_value.limit.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_get_paginated_orders_by_created_at_desc(self):
        # Given
        params = PaginationParams(page=1, size=5)

        # Mock database responses
        self.mock_db.query.return_value.count.return_value = 5
        mock_query = self.mock_db.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        # When
        await self.repository.get_paginated(params)

        # Then
        # Verify ordering by created_at desc was called
        mock_query.order_by.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_paginated_by_status_filters_correctly(self):
        # Given
        status = EbookStatus.DRAFT
        params = PaginationParams(page=1, size=5)

        # Mock database responses
        mock_filter_query = Mock()
        self.mock_db.query.return_value.filter.return_value = mock_filter_query
        mock_filter_query.count.return_value = 8
        mock_filter_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        # When
        result = await self.repository.get_paginated_by_status(status, params)

        # Then
        # Verify status filter was applied (called twice: for count and for data)
        assert self.mock_db.query.return_value.filter.call_count == 2
        assert result.total_count == 8

    @pytest.mark.asyncio
    async def test_get_paginated_by_status_applies_pagination_after_filter(self):
        # Given
        status = EbookStatus.APPROVED
        params = PaginationParams(page=2, size=3)

        # Mock database responses
        mock_filter_query = Mock()
        self.mock_db.query.return_value.filter.return_value = mock_filter_query
        mock_filter_query.count.return_value = 10
        mock_filter_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        # When
        await self.repository.get_paginated_by_status(status, params)

        # Then
        # Verify pagination parameters are applied to filtered query
        mock_filter_query.order_by.assert_called_once()
        mock_filter_query.order_by.return_value.offset.assert_called_once_with(3)  # (2-1) * 3
        mock_filter_query.order_by.return_value.offset.return_value.limit.assert_called_once_with(3)

    @pytest.mark.asyncio
    async def test_get_paginated_converts_models_to_domain_entities(self):
        # Given
        params = PaginationParams(page=1, size=2)
        mock_ebook_1 = self._create_mock_ebook_model(1, "Test Title 1")
        mock_ebook_2 = self._create_mock_ebook_model(2, "Test Title 2")

        # Mock database responses
        self.mock_db.query.return_value.count.return_value = 2
        mock_query = self.mock_db.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            mock_ebook_1,
            mock_ebook_2,
        ]

        # When
        result = await self.repository.get_paginated(params)

        # Then
        assert len(result.items) == 2
        ebook_1, ebook_2 = result.items

        assert isinstance(ebook_1, Ebook)
        assert ebook_1.id == 1
        assert ebook_1.title == "Test Title 1"

        assert isinstance(ebook_2, Ebook)
        assert ebook_2.id == 2
        assert ebook_2.title == "Test Title 2"

    @pytest.mark.asyncio
    async def test_get_paginated_handles_empty_results(self):
        # Given
        params = PaginationParams(page=1, size=10)

        # Mock database responses for empty results
        self.mock_db.query.return_value.count.return_value = 0
        mock_query = self.mock_db.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        # When
        result = await self.repository.get_paginated(params)

        # Then
        assert result.items == []
        assert result.total_count == 0
        assert result.page == 1
        assert result.size == 10

    @pytest.mark.asyncio
    async def test_get_paginated_by_status_handles_empty_results(self):
        # Given
        status = EbookStatus.DRAFT
        params = PaginationParams(page=1, size=10)

        # Mock database responses for empty results
        mock_filter_query = Mock()
        self.mock_db.query.return_value.filter.return_value = mock_filter_query
        mock_filter_query.count.return_value = 0
        mock_filter_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        # When
        result = await self.repository.get_paginated_by_status(status, params)

        # Then
        assert result.items == []
        assert result.total_count == 0
        assert result.page == 1
        assert result.size == 10

    def _create_mock_ebook_model(self, id_: int, title: str) -> Mock:
        """Helper method to create mock EbookModel instances"""
        mock_ebook = Mock(spec=EbookModel)
        mock_ebook.id = id_
        mock_ebook.title = title
        mock_ebook.author = "Test Author"
        mock_ebook.status = "DRAFT"
        mock_ebook.preview_url = f"http://example.com/preview/{id_}"
        mock_ebook.drive_id = f"drive-id-{id_}"
        mock_ebook.created_at = datetime.now(UTC)
        return mock_ebook
