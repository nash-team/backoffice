"""Domain event emitted when an ebook PDF is downloaded/exported."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class EbookExportedEvent(DomainEvent):
    """Event emitted when an ebook PDF is successfully exported/downloaded.

    This event is published after:
    - PDF bytes retrieved from database
    - Response prepared for download

    Subscribers can use this event for:
    - Usage analytics (track download counts)
    - Audit logging
    - Rate limiting
    - User notifications
    """

    ebook_id: int
    title: str
    file_size_bytes: int
    export_format: str  # "pdf" or "kdp"
