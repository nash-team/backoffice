"""Regeneration request value object."""

from dataclasses import dataclass

from backoffice.features.ebook_regeneration.domain.entities.page_type import PageType


@dataclass(frozen=True)
class RegenerationRequest:
    """Value object for page regeneration request.

    Attributes:
        ebook_id: ID of the ebook to regenerate
        page_type: Type of page to regenerate (cover, back_cover, content_page)
        page_index: Index of the page to regenerate (for content_page only)
        prompt_override: Optional custom prompt for generation
    """

    ebook_id: int
    page_type: PageType
    page_index: int | None = None
    prompt_override: str | None = None

    def __post_init__(self) -> None:
        """Validate regeneration request."""
        # Business rule: content_page requires page_index
        if self.page_type == PageType.CONTENT_PAGE and self.page_index is None:
            raise ValueError("page_index is required for content_page regeneration")

        # Business rule: cover and back_cover should not have page_index
        if self.page_type in (PageType.COVER, PageType.BACK_COVER) and self.page_index is not None:
            raise ValueError(
                f"page_index should not be provided for {self.page_type.value} regeneration"
            )
