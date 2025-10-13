"""Domain event emitted when an ebook is successfully created."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class EbookCreatedEvent(DomainEvent):
    """Event emitted when a new ebook has been successfully created.

    This event is published after:
    - Cover generation
    - Content pages generation
    - Back cover generation
    - PDF assembly
    - Storage upload (if available)
    - Database persistence

    Subscribers can use this event for:
    - Audit logging
    - Analytics tracking
    - Notifications
    - Post-creation workflows
    """

    ebook_id: int
    title: str
    theme_id: str
    audience: str
    number_of_pages: int
    preview_mode: bool
    has_drive_upload: bool
