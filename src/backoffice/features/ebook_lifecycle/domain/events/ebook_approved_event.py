"""Domain event emitted when an ebook is approved."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class EbookApprovedEvent(DomainEvent):
    """Event emitted when an ebook is approved and uploaded to storage.

    This event signals that an ebook has successfully completed the approval
    workflow and is now stored in Google Drive.

    Attributes:
        ebook_id: ID of the approved ebook
        drive_id: Google Drive file ID
        storage_url: Public URL to access the ebook
        title: Ebook title for reference
    """

    ebook_id: int
    drive_id: str | None
    storage_url: str | None
    title: str
