"""Back cover regenerated domain event."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class BackCoverRegeneratedEvent(DomainEvent):
    """Event emitted when an ebook back cover is regenerated.

    Attributes:
        ebook_id: ID of the ebook
        title: Title of the ebook
    """

    ebook_id: int
    title: str
