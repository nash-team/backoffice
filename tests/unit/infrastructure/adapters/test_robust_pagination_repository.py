"""
Robust unit tests for EbookRepository pagination using London methodology
with proper mocking and decoupled query logic.
"""

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.entities.pagination import PaginatedResult, PaginationParams
from backoffice.domain.ports.ebook_query_port import EbookQueryPort
from backoffice.infrastructure.adapters.repositories.ebook_repository import (
    SqlAlchemyEbookRepository,
)


class TestSqlAlchemyEbookRepositoryPagination:
    """Test suite for repository pagination using London methodology with autospec"""

    def setup_method(self):
        """Set up test fixtures with proper mocking"""
        # Use create_autospec for type-safe mocking
        self.mock_query_port = create_autospec(EbookQueryPort, instance=True)
        # Note: db is not needed since we're testing the repository abstraction
        # We pass None but inject the mock query port
        self.repository = SqlAlchemyEbookRepository(db=None, query_port=self.mock_query_port)  # type: ignore

    @pytest.mark.parametrize(
        "page,size,expected_offset",
        [
            (1, 10, 0),
            (2, 10, 10),
            (3, 5, 10),
            (1, 15, 0),
            (4, 25, 75),
        ],
    )
    async def test_get_paginated_delegates_to_query_port_with_correct_params(
        self, page: int, size: int, expected_offset: int
    ):
        """Test that pagination parameters are correctly passed to query port"""
        # Given
        params = PaginationParams(page=page, size=size)
        expected_result = PaginatedResult(
            items=[],
            total_count=100,
            page=page,
            size=size,
        )
        self.mock_query_port.list_paginated.return_value = expected_result

        # When
        result = await self.repository.get_paginated(params)

        # Then
        self.mock_query_port.list_paginated.assert_called_once_with(params)
        assert result == expected_result
        assert params.offset == expected_offset

    @pytest.mark.parametrize("status", [EbookStatus.PENDING, EbookStatus.APPROVED])
    async def test_get_paginated_by_status_delegates_correctly(self, status: EbookStatus):
        """Test that status filtering is properly delegated"""
        # Given
        params = PaginationParams(page=1, size=10)
        expected_result = PaginatedResult(
            items=[],
            total_count=50,
            page=1,
            size=10,
        )
        self.mock_query_port.list_paginated_by_status.return_value = expected_result

        # When
        result = await self.repository.get_paginated_by_status(status, params)

        # Then
        self.mock_query_port.list_paginated_by_status.assert_called_once_with(status, params)
        assert result == expected_result

    async def test_get_paginated_returns_query_port_result_unchanged(self):
        """Test that repository doesn't modify query port results"""
        # Given
        params = PaginationParams(page=2, size=5)
        mock_ebooks = [
            Ebook(
                id=1,
                title="Test 1",
                author="Author 1",
                status=EbookStatus.PENDING,
                created_at=datetime.now(UTC),
            ),
            Ebook(
                id=2,
                title="Test 2",
                author="Author 2",
                status=EbookStatus.APPROVED,
                created_at=datetime.now(UTC),
            ),
        ]
        expected_result = PaginatedResult(
            items=mock_ebooks,
            total_count=25,
            page=2,
            size=5,
        )
        self.mock_query_port.list_paginated.return_value = expected_result

        # When
        result = await self.repository.get_paginated(params)

        # Then
        assert result is expected_result  # Should be the exact same object
        assert result.items == mock_ebooks
        assert result.total_count == 25
        assert result.page == 2
        assert result.size == 5

    async def test_get_paginated_by_status_returns_query_port_result_unchanged(self):
        """Test that repository doesn't modify query port results for status filtering"""
        # Given
        status = EbookStatus.PENDING
        params = PaginationParams(page=3, size=7)
        mock_ebooks = [
            Ebook(
                id=3,
                title="Pending 1",
                author="Author 3",
                status=EbookStatus.PENDING,
                created_at=datetime.now(UTC),
            ),
        ]
        expected_result = PaginatedResult(
            items=mock_ebooks,
            total_count=15,
            page=3,
            size=7,
        )
        self.mock_query_port.list_paginated_by_status.return_value = expected_result

        # When
        result = await self.repository.get_paginated_by_status(status, params)

        # Then
        assert result is expected_result  # Should be the exact same object
        assert result.items == mock_ebooks
        assert result.total_count == 15

    @pytest.mark.parametrize(
        "page,size",
        [
            (1, 1),  # Minimum values
            (1, 100),  # Maximum page size
            (999, 50),  # Large page number
        ],
    )
    async def test_get_paginated_handles_edge_cases(self, page: int, size: int):
        """Test pagination with edge case parameters"""
        # Given
        params = PaginationParams(page=page, size=size)
        expected_result = PaginatedResult(items=[], total_count=0, page=page, size=size)
        self.mock_query_port.list_paginated.return_value = expected_result

        # When
        result = await self.repository.get_paginated(params)

        # Then
        self.mock_query_port.list_paginated.assert_called_once_with(params)
        assert result.page == page
        assert result.size == size

    async def test_query_port_not_called_multiple_times(self):
        """Test that query port is called exactly once per repository method call"""
        # Given
        params = PaginationParams(page=1, size=10)
        self.mock_query_port.list_paginated.return_value = PaginatedResult(
            items=[], total_count=0, page=1, size=10
        )

        # When
        await self.repository.get_paginated(params)
        await self.repository.get_paginated(params)

        # Then
        assert self.mock_query_port.list_paginated.call_count == 2

    async def test_repository_propagates_query_port_exceptions(self):
        """Test that repository propagates exceptions from query port"""
        # Given
        params = PaginationParams(page=1, size=10)
        expected_exception = ValueError("Database connection error")
        self.mock_query_port.list_paginated.side_effect = expected_exception

        # When/Then
        with pytest.raises(ValueError, match="Database connection error"):
            await self.repository.get_paginated(params)

    async def test_status_filtering_propagates_query_port_exceptions(self):
        """Test that status filtering propagates exceptions from query port"""
        # Given
        status = EbookStatus.PENDING
        params = PaginationParams(page=1, size=10)
        expected_exception = ValueError("Invalid status filter")
        self.mock_query_port.list_paginated_by_status.side_effect = expected_exception

        # When/Then
        with pytest.raises(ValueError, match="Invalid status filter"):
            await self.repository.get_paginated_by_status(status, params)
