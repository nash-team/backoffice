"""Domain events for ebook lifecycle feature."""

from backoffice.features.ebook.lifecycle.domain.events.ebook_approved_event import (
    EbookApprovedEvent,
)
from backoffice.features.ebook.lifecycle.domain.events.ebook_rejected_event import (
    EbookRejectedEvent,
)

__all__ = ["EbookApprovedEvent", "EbookRejectedEvent"]
