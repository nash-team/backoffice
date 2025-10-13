# Ebook Lifecycle Feature

> Bounded context for managing ebook approval workflow and lifecycle states

## Overview

The `ebook/lifecycle` feature is a bounded context that manages the lifecycle states of ebooks (DRAFT → APPROVED → REJECTED) and provides approval/rejection workflows with file storage integration.

## Bounded Context

### Responsibilities

- Approve draft ebooks and upload to Google Drive
- Reject ebooks during validation workflow
- Provide lifecycle statistics (counts by status)
- Emit domain events for lifecycle state changes

### Domain Events

- **EbookApprovedEvent**: Emitted after successful approval and Drive upload
- **EbookRejectedEvent**: Emitted after ebook rejection

### Use Cases

- **ApproveEbookUseCase**: Approve DRAFT ebook → upload to Drive → update status
- **RejectEbookUseCase**: Reject DRAFT/APPROVED ebook → update status
- **GetStatsUseCase**: Get ebook counts by status for dashboard

## Architecture

```
ebook/lifecycle/
├── domain/
│   ├── events/              # EbookApprovedEvent, EbookRejectedEvent
│   └── usecases/            # ApproveEbookUseCase, RejectEbookUseCase, GetStatsUseCase
├── infrastructure/
│   └── event_handlers/      # (Future: notification handlers, analytics)
├── presentation/
│   └── routes/              # API routes for approval/rejection/stats
└── tests/
    ├── unit/                # Use case tests with fakes
    ├── integration/         # Route tests with DB
    └── e2e/                 # E2E approval workflow tests
```

## API Routes

### Lifecycle Management

```http
PUT /api/dashboard/ebooks/{ebook_id}/approve
PUT /api/dashboard/ebooks/{ebook_id}/reject
GET /api/dashboard/stats
```

All routes return HTMX-compatible HTML partials for dynamic UI updates.

## Usage

### Approve an Ebook

```python
from backoffice.features.ebook.lifecycle.domain.usecases.approve_ebook_usecase import (
    ApproveEbookUseCase,
)
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

# Setup
ebook_repository = factory.get_ebook_repository()
file_storage = factory.get_file_storage()
event_bus = EventBus()

approve_usecase = ApproveEbookUseCase(ebook_repository, file_storage, event_bus)

# Execute
updated_ebook = await approve_usecase.execute(ebook_id=123)
# → Uploads to Drive
# → Updates status to APPROVED
# → Emits EbookApprovedEvent
```

### Reject an Ebook

```python
from backoffice.features.ebook.lifecycle.domain.usecases.reject_ebook_usecase import (
    RejectEbookUseCase,
)

reject_usecase = RejectEbookUseCase(ebook_repository, event_bus)

# Execute
updated_ebook = await reject_usecase.execute(ebook_id=123, reason="Quality issues")
# → Updates status to REJECTED
# → Emits EbookRejectedEvent
```

### Get Lifecycle Stats

```python
from backoffice.features.ebook.lifecycle.domain.usecases.get_stats_usecase import (
    GetStatsUseCase,
)

get_stats_usecase = GetStatsUseCase(ebook_repository)

stats = await get_stats_usecase.execute()
# → Returns: Stats(total_ebooks=10, draft_ebooks=3, approved_ebooks=5, rejected_ebooks=2)
```

## Event-Driven Integration

### Listening to Approval Events

```python
from backoffice.features.ebook.lifecycle.domain.events.ebook_approved_event import (
    EbookApprovedEvent,
)
from backoffice.features.shared.infrastructure.events.event_handler import EventHandler

class SendApprovalNotificationHandler(EventHandler[EbookApprovedEvent]):
    async def handle(self, event: EbookApprovedEvent) -> None:
        # Send email notification
        await send_email(
            subject=f"Ebook '{event.title}' approved!",
            body=f"View at: {event.storage_url}",
        )

# Subscribe
event_bus.subscribe(EbookApprovedEvent, SendApprovalNotificationHandler())
```

## Testing

### Run Unit Tests

```bash
pytest src/backoffice/features/ebook/lifecycle/tests/unit/ -v
```

### Run Integration Tests

```bash
pytest src/backoffice/features/ebook/lifecycle/tests/integration/ -v
```

## Migration Status

**Current State**: ✅ Complete (Phase 8/8)

- ✅ Domain layer complete (events + use cases)
- ✅ Infrastructure layer created (event handlers stub)
- ✅ Presentation layer migrated (routes from dashboard.py)
- ✅ Routes registered in app
- ✅ Tests migrated and passing (9/9)
- ✅ Legacy code cleaned (dashboard.py commented out)
- ✅ All quality checks passing (mypy, ruff, pytest)

## DDD Principles Applied

1. **Bounded Context**: Lifecycle management isolated from other features
2. **Ubiquitous Language**: ApproveEbook, RejectEbook, EbookStatus
3. **Domain Events**: EbookApprovedEvent, EbookRejectedEvent for decoupling
4. **Use Cases**: Single entry point for each business action
5. **Ports & Adapters**: Depends on EbookPort and FileStoragePort abstractions

## Integration with Other Features

- **File Storage**: Uses `FileStoragePort` for Google Drive uploads
- **Ebook Repository**: Uses `EbookPort` for ebook persistence
- **Event Bus**: Publishes events consumed by other features

---

**Feature Template**: Based on `generation_costs` feature architecture
**Migration Guide**: See `docs/FEATURE_MIGRATION_GUIDE.md`
