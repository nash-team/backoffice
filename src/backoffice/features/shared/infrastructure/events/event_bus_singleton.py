"""Singleton instance of EventBus for application-wide event publishing."""

from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# Global singleton instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global EventBus instance.

    Returns:
        EventBus: The singleton EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the EventBus singleton (useful for testing)."""
    global _event_bus
    if _event_bus is not None:
        _event_bus.clear()
    _event_bus = None
