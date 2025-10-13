"""Domain event emitted when an ebook is rejected."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class EbookRejectedEvent(DomainEvent):
    """Event emitted when an ebook is rejected during validation.

    This event signals that an ebook failed the approval workflow
    and has been marked as REJECTED.

    Attributes:
        ebook_id: ID of the rejected ebook
        reason: Reason for rejection
        title: Ebook title for reference
    """

    ebook_id: int
    reason: str
    title: str
