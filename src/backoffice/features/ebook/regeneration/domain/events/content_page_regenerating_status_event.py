"""Content page regenerated domain event."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ContentPageRegeneratingStatusEvent(DomainEvent):
    """Event emitted when regenerating an image.

    Attributes:
        ebook_id: ID of the ebook
        page_index: Index of the regenerated page
        status: int between 0 and 100
        current_step: current block being executed
    """

    ebook_id: int
    page_index: int
    status: int
    state: str | None = None
    nb_total_steps: int
    current_step: int | None = None
