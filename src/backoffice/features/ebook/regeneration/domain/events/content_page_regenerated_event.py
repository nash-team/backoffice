"""Content page regenerated domain event."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ContentPageRegeneratedEvent(DomainEvent):
    """Event emitted when a content/coloring page is regenerated.

    Attributes:
        ebook_id: ID of the ebook
        title: Title of the ebook
        page_index: Index of the regenerated page
        prompt_used: Prompt used for regeneration
    """

    ebook_id: int
    title: str
    page_index: int
    prompt_used: str
