from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class PaginationParams:
    """Parameters for pagination requests"""

    page: int = 1
    size: int = 15

    def __post_init__(self):
        """Validate pagination parameters"""
        if self.page < 1:
            raise ValueError("Page number must be at least 1")
        if self.size < 1:
            raise ValueError("Page size must be at least 1")
        if self.size > 100:
            raise ValueError("Page size cannot exceed 100")

    @property
    def offset(self) -> int:
        """Calculate the offset for database queries"""
        return (self.page - 1) * self.size


@dataclass
class PaginatedResult(Generic[T]):
    """Container for paginated results with metadata"""

    items: list[T]
    total_count: int
    page: int
    size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        if self.total_count == 0:
            return 0
        return (self.total_count + self.size - 1) // self.size

    @property
    def has_next(self) -> bool:
        """Check if there are more pages"""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there are previous pages"""
        return self.page > 1

    @property
    def next_page(self) -> int | None:
        """Get next page number if available"""
        return self.page + 1 if self.has_next else None

    @property
    def previous_page(self) -> int | None:
        """Get previous page number if available"""
        return self.page - 1 if self.has_previous else None

    @property
    def start_item(self) -> int:
        """Get the index of the first item on current page"""
        if self.total_count == 0:
            return 0
        return (self.page - 1) * self.size + 1

    @property
    def end_item(self) -> int:
        """Get the index of the last item on current page"""
        if self.total_count == 0:
            return 0
        return min(self.page * self.size, self.total_count)
