# Generation Costs Feature

> Bounded context for tracking token usage and API costs during ebook generation

## Overview

The `generation_costs` feature is a bounded context that tracks token consumption and costs for all API calls made during ebook generation. It operates independently from other features using event-driven communication.

## Bounded Context

### Responsibilities

- Track token usage per API call (prompt tokens, completion tokens, cost)
- Track image generation usage (input images, output images, cost)
- Calculate total costs for generation requests
- Persist usage data for cost analysis
- Provide cost summaries via API

### Domain Entities

- **TokenUsage**: Single API call token consumption record
- **ImageUsage**: Single API call image generation record
- **CostCalculation**: Aggregates all usage for a generation request

### Domain Events

- **TokensConsumedEvent**: Emitted after each API call consuming tokens
- **CostCalculatedEvent**: Emitted after all costs for a request are calculated

### Ports (Interfaces)

- **TokenTrackerPort**: Interface for persisting and retrieving usage data

## Architecture

```
generation_costs/
├── domain/
│   ├── entities/           # TokenUsage, ImageUsage, CostCalculation
│   ├── events/             # TokensConsumedEvent, CostCalculatedEvent
│   ├── ports/              # TokenTrackerPort
│   └── usecases/           # TrackTokenUsageUseCase, CalculateGenerationCostUseCase
├── infrastructure/
│   ├── adapters/           # TokenTrackerRepository (SQLAlchemy)
│   ├── models/             # TokenUsageModel, ImageUsageModel
│   └── event_handlers/     # (Future: EbookGeneratedHandler)
└── presentation/
    ├── routes/             # costs_routes.py
    └── templates/          # costs.html
```

## Database Schema

### token_usages

```sql
CREATE TABLE token_usages (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost NUMERIC(10, 6) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    ebook_id INTEGER NULL
);
CREATE INDEX ix_token_usages_request_id ON token_usages(request_id);
CREATE INDEX ix_token_usages_ebook_id ON token_usages(ebook_id);
```

### image_usages

```sql
CREATE TABLE image_usages (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    input_images INTEGER NOT NULL,
    output_images INTEGER NOT NULL,
    cost NUMERIC(10, 6) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    ebook_id INTEGER NULL
);
CREATE INDEX ix_image_usages_request_id ON image_usages(request_id);
CREATE INDEX ix_image_usages_ebook_id ON image_usages(ebook_id);
```

## Usage

### Tracking Token Usage

```python
from backoffice.features.generation_costs.domain.usecases.track_token_usage_usecase import TrackTokenUsageUseCase
from backoffice.features.generation_costs.infrastructure.adapters.token_tracker_repository import TokenTrackerRepository
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# Setup
event_bus = EventBus()
token_tracker = TokenTrackerRepository(db)
track_usage_usecase = TrackTokenUsageUseCase(token_tracker, event_bus)

# Track usage after API call
await track_usage_usecase.execute(
    request_id="req-123",
    model="gpt-4",
    prompt_tokens=100,
    completion_tokens=50,
    cost=Decimal("0.01")
)
# → Saves to DB + emits TokensConsumedEvent
```

### Calculating Total Cost

```python
from backoffice.features.generation_costs.domain.usecases.calculate_generation_cost_usecase import CalculateGenerationCostUseCase

# Calculate total cost for request
calculate_cost_usecase = CalculateGenerationCostUseCase(token_tracker, event_bus)
await calculate_cost_usecase.execute(
    request_id="req-123",
    ebook_id=456
)
# → Emits CostCalculatedEvent with totals
```

### Getting Cost Summaries

```python
# Get all cost calculations
calculations = await token_tracker.get_all_cost_calculations()

for calc in calculations:
    print(f"Request {calc.request_id}:")
    print(f"  Total cost: ${calc.total_cost}")
    print(f"  Total tokens: {calc.total_tokens}")
    print(f"  API calls: {calc.api_call_count}")
```

## Event-Driven Integration

### Listening to Events

```python
from backoffice.features.shared.infrastructure.events.event_handler import EventHandler
from backoffice.features.generation_costs.domain.events.tokens_consumed_event import TokensConsumedEvent

class MyEventHandler(EventHandler[TokensConsumedEvent]):
    async def handle(self, event: TokensConsumedEvent) -> None:
        print(f"Tokens consumed: {event.total_tokens}")

# Subscribe
event_bus.subscribe(TokensConsumedEvent, MyEventHandler())
```

## Testing

### Unit Tests

```bash
pytest tests/backoffice_features/generation_costs/unit/ -v
```

### Integration Tests

```bash
pytest tests/backoffice_features/generation_costs/integration/ -v
```

## Migration Status

**Current State**: ✅ Complete

- ✅ Domain layer complete
- ✅ Infrastructure layer complete (DB models + repository)
- ✅ Presentation layer migrated (costs page using TokenTrackerRepository)
- ✅ Event integration ACTIVE (OpenRouterImageProvider emits TokensConsumedEvent)
- ✅ Old code REMOVED (token_tracker.py and get_ebook_costs.py deleted)
- ✅ Event-driven architecture implemented

## DDD Principles Applied

1. **Bounded Context**: Generation costs is isolated from other features
2. **Ubiquitous Language**: TokenUsage, CostCalculation, request_id
3. **Aggregates**: CostCalculation aggregates multiple TokenUsage/ImageUsage
4. **Domain Events**: TokensConsumedEvent, CostCalculatedEvent
5. **Ports & Adapters**: TokenTrackerPort implemented by TokenTrackerRepository
