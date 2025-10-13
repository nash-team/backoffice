"""Domain event emitted when a KDP export is generated."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class KDPExportGeneratedEvent(DomainEvent):
    """Event emitted when a KDP (Amazon Kindle Direct Publishing) export is generated.

    This event is published after:
    - PDF assembled with KDP specifications (bleed, trim, etc.)
    - Quality checks passed
    - Response prepared for download

    Subscribers can use this event for:
    - KDP submission tracking
    - Analytics (track which ebooks are published)
    - Audit logging (compliance)
    - Automated quality reports
    """

    ebook_id: int
    title: str
    file_size_bytes: int
    preview_mode: bool  # True if generated for preview, False if for final download
    status: str  # Ebook status (DRAFT or APPROVED)
