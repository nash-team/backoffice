"""Unit tests for EventBus."""

import pytest

from backoffice.features.shared.infrastructure.events.domain_event import DomainEvent
from backoffice.features.shared.infrastructure.events.event_bus import EventBus
from backoffice.features.shared.infrastructure.events.event_handler import EventHandler


# Test events
class UserRegisteredEvent(DomainEvent):
    """Test event: user registered."""

    def __init__(self, user_id: str, email: str):
        super().__init__(aggregate_id=user_id)
        self.user_id = user_id
        self.email = email


class OrderPlacedEvent(DomainEvent):
    """Test event: order placed."""

    def __init__(self, order_id: str, amount: float):
        super().__init__(aggregate_id=order_id)
        self.order_id = order_id
        self.amount = amount


# Test handlers
class FakeUserRegisteredHandler(EventHandler[UserRegisteredEvent]):
    """Fake handler for user registered events."""

    def __init__(self):
        self.handled_events: list[UserRegisteredEvent] = []
        self.should_fail = False

    async def handle(self, event: UserRegisteredEvent) -> None:
        """Handle user registered event."""
        if self.should_fail:
            raise ValueError("Handler intentionally failed")
        self.handled_events.append(event)


class FakeOrderPlacedHandler(EventHandler[OrderPlacedEvent]):
    """Fake handler for order placed events."""

    def __init__(self):
        self.handled_events: list[OrderPlacedEvent] = []

    async def handle(self, event: OrderPlacedEvent) -> None:
        """Handle order placed event."""
        self.handled_events.append(event)


@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test."""
    return EventBus()


@pytest.mark.asyncio
class TestEventBus:
    """Test suite for EventBus."""

    async def test_subscribe_and_publish_single_handler(self, event_bus: EventBus):
        """Test subscribing a handler and publishing an event."""
        # Given
        handler = FakeUserRegisteredHandler()
        event_bus.subscribe(UserRegisteredEvent, handler)

        # When
        event = UserRegisteredEvent(user_id="123", email="test@example.com")
        await event_bus.publish(event)

        # Then
        assert len(handler.handled_events) == 1
        assert handler.handled_events[0].user_id == "123"
        assert handler.handled_events[0].email == "test@example.com"

    async def test_subscribe_multiple_handlers_same_event(self, event_bus: EventBus):
        """Test multiple handlers for same event type."""
        # Given
        handler1 = FakeUserRegisteredHandler()
        handler2 = FakeUserRegisteredHandler()
        event_bus.subscribe(UserRegisteredEvent, handler1)
        event_bus.subscribe(UserRegisteredEvent, handler2)

        # When
        event = UserRegisteredEvent(user_id="456", email="user@example.com")
        await event_bus.publish(event)

        # Then
        assert len(handler1.handled_events) == 1
        assert len(handler2.handled_events) == 1
        assert handler1.handled_events[0].user_id == "456"
        assert handler2.handled_events[0].user_id == "456"

    async def test_publish_different_event_types(self, event_bus: EventBus):
        """Test publishing different event types to different handlers."""
        # Given
        user_handler = FakeUserRegisteredHandler()
        order_handler = FakeOrderPlacedHandler()
        event_bus.subscribe(UserRegisteredEvent, user_handler)
        event_bus.subscribe(OrderPlacedEvent, order_handler)

        # When
        user_event = UserRegisteredEvent(user_id="123", email="test@example.com")
        order_event = OrderPlacedEvent(order_id="456", amount=99.99)
        await event_bus.publish(user_event)
        await event_bus.publish(order_event)

        # Then
        assert len(user_handler.handled_events) == 1
        assert len(order_handler.handled_events) == 1
        assert user_handler.handled_events[0].user_id == "123"
        assert order_handler.handled_events[0].order_id == "456"

    async def test_publish_with_no_handlers(self, event_bus: EventBus):
        """Test publishing event with no registered handlers (should not raise)."""
        # Given
        event = UserRegisteredEvent(user_id="789", email="nohandler@example.com")

        # When/Then - should not raise
        await event_bus.publish(event)

    async def test_handler_failure_does_not_stop_other_handlers(self, event_bus: EventBus):
        """Test that one handler failing doesn't stop others."""
        # Given
        failing_handler = FakeUserRegisteredHandler()
        failing_handler.should_fail = True
        success_handler = FakeUserRegisteredHandler()

        event_bus.subscribe(UserRegisteredEvent, failing_handler)
        event_bus.subscribe(UserRegisteredEvent, success_handler)

        # When
        event = UserRegisteredEvent(user_id="999", email="test@example.com")
        await event_bus.publish(event)

        # Then - success handler should still execute
        assert len(success_handler.handled_events) == 1
        assert success_handler.handled_events[0].user_id == "999"

    async def test_clear_handlers(self, event_bus: EventBus):
        """Test clearing all registered handlers."""
        # Given
        handler = FakeUserRegisteredHandler()
        event_bus.subscribe(UserRegisteredEvent, handler)

        # When
        event_bus.clear()
        event = UserRegisteredEvent(user_id="cleared", email="test@example.com")
        await event_bus.publish(event)

        # Then - handler should not be called
        assert len(handler.handled_events) == 0

    async def test_event_has_unique_id_and_timestamp(self):
        """Test that events have unique IDs and timestamps."""
        # Given/When
        event1 = UserRegisteredEvent(user_id="1", email="a@example.com")
        event2 = UserRegisteredEvent(user_id="2", email="b@example.com")

        # Then
        assert event1.event_id != event2.event_id
        assert event1.occurred_at is not None
        assert event2.occurred_at is not None
        assert event1.aggregate_id == "1"
        assert event2.aggregate_id == "2"

    async def test_event_name(self):
        """Test event name method."""
        # Given
        event = UserRegisteredEvent(user_id="123", email="test@example.com")

        # When/Then
        assert event.event_name() == "UserRegisteredEvent"
