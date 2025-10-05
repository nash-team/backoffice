# Ebook Creation Feature

Feature-based module for creating new coloring book ebooks.

## Overview

This feature handles the complete workflow for creating a new coloring book ebook:
- Input validation via value objects
- Cover generation (colored)
- Content pages generation (black & white line art)
- Back cover generation (line art version of cover)
- PDF assembly
- Google Drive upload
- Database persistence
- Event emission for tracking

## Architecture

```
ebook_creation/
├── domain/
│   ├── entities/
│   │   └── creation_request.py      # Value object with validation
│   ├── events/
│   │   └── ebook_created_event.py   # Domain event
│   └── usecases/
│       └── create_ebook.py          # Use case with event emission
└── presentation/
    └── routes/
        └── __init__.py              # FastAPI routes
```

## Use Case

### CreateEbookUseCase

**Purpose**: Create a new coloring book ebook with full workflow execution.

**Input**: `GenerationRequest` (from domain layer)

**Output**: `Ebook` entity

**Workflow**:
1. Generate ebook using strategy pattern (cover + pages + back cover)
2. Create ebook entity with DRAFT status
3. Store pages metadata in `structure_json`
4. Persist to database
5. Save PDF bytes to database
6. Upload to Google Drive (if available)
7. **Emit `EbookCreatedEvent`**
8. Return created ebook

**Example**:
```python
from backoffice.features.ebook_creation.domain.usecases.create_ebook import CreateEbookUseCase
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

event_bus = EventBus()
use_case = CreateEbookUseCase(
    ebook_repository=ebook_repo,
    generation_strategy=strategy,
    event_bus=event_bus,
    file_storage=file_storage,
)

ebook = await use_case.execute(generation_request, is_preview=False)
```

## API Routes

### POST /api/ebooks

Create a new coloring book ebook.

**Request** (Form data):
```
ebook_type: str = "coloring"      # Only coloring type supported
theme_id: str                     # Required: dinosaurs, unicorns, pirates
audience: str                     # Required: 3-5, 6-8, 9-12
title: str | None                 # Optional (auto-generated if not provided)
author: str = "Assistant IA"      # Default author
number_of_pages: int = 8          # Default 8 pages
preview_mode: bool = False        # True = 1 page, False = full book
```

**Response**: HTML partial (ebooks table updated)

**HTMX Integration**:
```html
<form hx-post="/api/ebooks"
      hx-target="#ebooksTableContainer"
      hx-swap="innerHTML">
  <!-- Form fields -->
</form>
```

**Example CURL**:
```bash
curl -X POST http://localhost:8000/api/ebooks \
  -F "ebook_type=coloring" \
  -F "theme_id=dinosaurs" \
  -F "audience=6-8" \
  -F "title=My Dinosaur Book" \
  -F "number_of_pages=24" \
  -F "preview_mode=false"
```

## Domain Events

### EbookCreatedEvent

**Emitted when**: An ebook is successfully created and persisted.

**Payload**:
```python
@dataclass(frozen=True, kw_only=True)
class EbookCreatedEvent(DomainEvent):
    ebook_id: int                 # Database ID
    title: str                    # Ebook title
    theme_id: str                 # Theme used (dinosaurs, etc.)
    audience: str                 # Target age group
    number_of_pages: int          # Total pages (including cover + back)
    preview_mode: bool            # Whether created in preview mode
    has_drive_upload: bool        # Whether uploaded to Drive
```

**Subscribers**: Could be used for:
- Analytics tracking
- Notification systems
- Post-creation workflows (e.g., auto-approval for previews)
- Audit logging

**Example Subscriber**:
```python
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

event_bus = EventBus()

@event_bus.subscribe
async def log_ebook_creation(event: EbookCreatedEvent) -> None:
    logger.info(f"📚 New ebook created: {event.title} (ID: {event.ebook_id})")
    logger.info(f"   Theme: {event.theme_id}, Pages: {event.number_of_pages}")
```

## Domain Entities

### CreationRequest

**Purpose**: Value object for validating ebook creation requests.

**Business Rules**:
- Only `coloring` ebook type is supported
- `theme_id` must be non-empty
- `audience` must be non-empty
- `number_of_pages` must be positive

**Example**:
```python
from backoffice.features.ebook_creation.domain.entities.creation_request import CreationRequest

# Valid request
request = CreationRequest(
    ebook_type="coloring",
    theme_id="dinosaurs",
    audience="6-8",
    title="Dino Adventures",
    number_of_pages=24,
    preview_mode=False,
)

# Invalid - raises ValueError
try:
    bad_request = CreationRequest(
        ebook_type="magazine",  # ❌ Not supported
        theme_id="dinosaurs",
        audience="6-8",
    )
except ValueError as e:
    print(e)  # "Invalid ebook_type 'magazine'. Only 'coloring' type is currently supported."
```

## Testing

### Unit Tests

Test use case with fakes:
```python
from tests.unit.fakes.fake_strategy import FakeColoringBookStrategy
from backoffice.features.ebook_creation.domain.usecases.create_ebook import CreateEbookUseCase

async def test_create_ebook_emits_event():
    event_bus = EventBus()
    events_published = []

    async def capture_event(event):
        events_published.append(event)

    event_bus.subscribe(EbookCreatedEvent)(capture_event)

    use_case = CreateEbookUseCase(
        ebook_repository=fake_repo,
        generation_strategy=FakeColoringBookStrategy(),
        event_bus=event_bus,
        file_storage=fake_storage,
    )

    ebook = await use_case.execute(generation_request)

    assert len(events_published) == 1
    assert events_published[0].ebook_id == ebook.id
```

### Integration Tests

Test route with real database:
```python
async def test_create_ebook_endpoint(client: AsyncClient, db_session):
    response = await client.post(
        "/api/ebooks",
        data={
            "ebook_type": "coloring",
            "theme_id": "dinosaurs",
            "audience": "6-8",
            "number_of_pages": 24,
        },
    )

    assert response.status_code == 200
    assert "Coloring Book" in response.text
```

## Migration Notes

### Migrated From

- **Legacy endpoint**: `POST /api/dashboard/ebooks` (dashboard.py)
- **Legacy use case**: `src/backoffice/domain/usecases/create_ebook.py`

### Changes Made

1. **Added Event Emission**: `EbookCreatedEvent` published after creation
2. **Added Validation**: `CreationRequest` value object enforces business rules
3. **New Route Path**: `/api/ebooks` (shorter, feature-based)
4. **Updated Frontend**: Template now calls `/api/ebooks`

### Legacy Code Status

Legacy endpoint in `dashboard.py` is commented out but kept for reference.

## Dependencies

### Internal
- `backoffice.domain.entities.ebook` - Ebook entity
- `backoffice.domain.entities.generation_request` - GenerationRequest
- `backoffice.domain.ports.ebook.ebook_port` - EbookPort interface
- `backoffice.domain.ports.ebook_generation_strategy_port` - Strategy interface
- `backoffice.domain.ports.file_storage_port` - FileStoragePort interface
- `backoffice.application.strategies.strategy_factory` - StrategyFactory
- `backoffice.features.shared.infrastructure.events.event_bus` - EventBus

### External
- `fastapi` - Web framework
- `pydantic` - Validation (via Form parameters)

## Future Improvements

- [ ] Add support for other ebook types (not just coloring)
- [ ] Add batch creation endpoint (create multiple ebooks at once)
- [ ] Add creation templates (preset configurations)
- [ ] Add creation scheduling (delayed generation)
- [ ] Add creation quotas (rate limiting)
- [ ] Add creation analytics (track popular themes/audiences)
