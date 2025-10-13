"""Page type enumeration for ebook regeneration."""

from enum import Enum


class PageType(str, Enum):
    """Types of pages that can be regenerated in an ebook."""

    COVER = "cover"
    BACK_COVER = "back_cover"
    CONTENT_PAGE = "content_page"

    def __str__(self) -> str:
        """String representation."""
        return self.value
