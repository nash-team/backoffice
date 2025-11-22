"""Cover regenerated domain event."""

from dataclasses import dataclass

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CoverRegeneratedEvent(DomainEvent):
    """Event emitted when an ebook cover is regenerated.

    Attributes:
        ebook_id: ID of the ebook
        title: Title of the ebook
        prompt_used: Prompt used for regeneration (for tracking)
    """

    ebook_id: int
    title: str
    prompt_used: str
