# Ebook Export Feature

Feature-based module for exporting ebook PDFs in various formats (raw PDF, KDP format).

## Overview

This feature handles ebook export workflows:
- **Raw PDF export**: Download ebook PDF from database (for DRAFT previews)
- **KDP export**: Generate Amazon Kindle Direct Publishing formatted PDFs with bleed/trim specifications
- Event emission for tracking exports
- Support for preview mode (inline viewing) and download mode

## Architecture

```
ebook_export/
├── domain/
│   ├── entities/
│   │   └── export_request.py           # Value object with validation
│   ├── events/
│   │   ├── ebook_exported_event.py     # Event for raw PDF exports
│   │   └── kdp_export_generated_event.py  # Event for KDP exports
│   └── usecases/
│       ├── export_ebook_pdf.py         # Raw PDF export use case
│       └── export_to_kdp.py            # KDP format export use case
└── presentation/
    └── routes/
        └── __init__.py                  # 2 GET routes
```

## Use Cases

### ExportEbookPdfUseCase

**Purpose**: Export raw ebook PDF from database.

**Input**: `ebook_id: int`

**Output**: `bytes` (PDF content)

**Workflow**:
1. Validate ebook exists
2. Retrieve PDF bytes from database
3. **Emit `EbookExportedEvent`**
4. Return PDF bytes

**Example**:
```python
from backoffice.features.ebook.export.domain.usecases.export_ebook_pdf import ExportEbookPdfUseCase
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

event_bus = EventBus()
use_case = ExportEbookPdfUseCase(ebook_repository=ebook_repo, event_bus=event_bus)

pdf_bytes = await use_case.execute(ebook_id=123)
```

**Errors**:
- `EBOOK_NOT_FOUND`: Ebook doesn't exist
- `VALIDATION_ERROR`: PDF not available (may have been deleted)

### ExportToKDPUseCase

**Purpose**: Export ebook to Amazon KDP paperback format with proper specifications.

**Input**:
- `ebook_id: int`
- `kdp_config: KDPExportConfig | None` (optional)
- `preview_mode: bool = False`

**Output**: `bytes` (KDP-formatted PDF)

**Workflow**:
1. Load ebook and validate status
   - Preview mode: Allows DRAFT or APPROVED
   - Download mode: Requires APPROVED only
2. Validate page_count exists
3. Adjust paper type if needed (premium_color requires 24+ pages)
4. Initialize image and assembly providers
5. Extract front cover (with text)
6. Extract back cover (line art)
7. Assemble KDP PDF (back + spine + front) with bleed/trim
8. **Emit `KDPExportGeneratedEvent`**
9. Return PDF bytes

**Example**:
```python
from backoffice.features.ebook.export.domain.usecases.export_to_kdp import ExportToKDPUseCase
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

event_bus = EventBus()
use_case = ExportToKDPUseCase(ebook_repository=ebook_repo, event_bus=event_bus)

# Preview mode (allows DRAFT)
kdp_pdf = await use_case.execute(ebook_id=123, preview_mode=True)

# Download mode (requires APPROVED)
kdp_pdf = await use_case.execute(ebook_id=123, preview_mode=False)
```

**Errors**:
- `EBOOK_NOT_FOUND`: Ebook doesn't exist
- `VALIDATION_ERROR`: Invalid status, missing page_count, or missing pages metadata

## API Routes

### GET /api/ebooks/{ebook_id}/pdf

Export raw ebook PDF from database.

**Use case**: Preview DRAFT ebooks before Drive upload.

**Query Parameters**: None

**Response**: PDF file (inline disposition, cached for 1 hour)

**Headers**:
- `Content-Type: application/pdf`
- `Content-Disposition: inline; filename="<title>.pdf"`
- `Cache-Control: public, max-age=3600`

**Example**:
```bash
curl http://localhost:8000/api/ebooks/123/pdf > ebook.pdf
```

**Errors**:
- `404 NOT FOUND`: Ebook doesn't exist
- `404 NOT FOUND`: PDF not available
- `500 INTERNAL ERROR`: Server error

### GET /api/ebooks/{ebook_id}/export-kdp

Export ebook to KDP format.

**Use case**: Generate final PDF for Amazon KDP paperback publication.

**Query Parameters**:
- `preview: bool = false` - If true, inline viewing (allows DRAFT); if false, download (requires APPROVED)

**Response**: KDP-formatted PDF

**Headers** (preview=false):
- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="<title>_KDP.pdf"`
- `Cache-Control: no-cache`

**Headers** (preview=true):
- `Content-Disposition: inline; filename="<title>_KDP.pdf"`

**Example**:
```bash
# Preview mode (inline, allows DRAFT)
curl "http://localhost:8000/api/ebooks/123/export-kdp?preview=true"

# Download mode (attachment, requires APPROVED)
curl "http://localhost:8000/api/ebooks/123/export-kdp" > ebook_kdp.pdf
```

**Errors**:
- `400 BAD REQUEST`: Invalid status (not APPROVED for download)
- `400 BAD REQUEST`: Missing page_count or pages metadata
- `500 INTERNAL ERROR`: Assembly failure
- `501 NOT IMPLEMENTED`: Feature not yet implemented (rare)

## Domain Events

### EbookExportedEvent

**Emitted when**: Raw PDF is successfully exported from database.

**Payload**:
```python
@dataclass(frozen=True, kw_only=True)
class EbookExportedEvent(DomainEvent):
    ebook_id: int              # Ebook ID
    title: str                 # Ebook title
    file_size_bytes: int       # PDF size in bytes
    export_format: str         # "pdf" or "kdp"
```

**Use cases**:
- Track download counts per ebook
- Audit logging
- Rate limiting (prevent abuse)
- Analytics (popular ebooks)

### KDPExportGeneratedEvent

**Emitted when**: KDP export is successfully generated.

**Payload**:
```python
@dataclass(frozen=True, kw_only=True)
class KDPExportGeneratedEvent(DomainEvent):
    ebook_id: int              # Ebook ID
    title: str                 # Ebook title
    file_size_bytes: int       # PDF size in bytes
    preview_mode: bool         # True if preview, False if download
    status: str                # Ebook status (DRAFT or APPROVED)
```

**Use cases**:
- Track KDP submissions (publication pipeline)
- Quality monitoring (file sizes)
- Audit compliance (who exported what)
- Analytics (export trends)

## Domain Entities

### ExportRequest

**Purpose**: Value object for validating export requests.

**Business Rules**:
- `ebook_id` must be positive
- `export_type` must be valid (`ExportType.PDF` or `ExportType.KDP`)
- `preview_mode` only applies to KDP exports

**Example**:
```python
from backoffice.features.ebook.export.domain.entities.export_request import (
    ExportRequest,
    ExportType,
)

# Valid request
request = ExportRequest(
    ebook_id=123,
    export_type=ExportType.KDP,
    preview_mode=True,
)

# Invalid - raises ValueError
try:
    bad_request = ExportRequest(
        ebook_id=123,
        export_type=ExportType.PDF,
        preview_mode=True,  # ❌ preview_mode only for KDP
    )
except ValueError as e:
    print(e)  # "preview_mode only applies to KDP exports"
```

### ExportType Enum

```python
class ExportType(str, Enum):
    PDF = "pdf"      # Raw PDF from database
    KDP = "kdp"      # Amazon KDP format
```

## Frontend Integration

### Raw PDF Preview (DRAFT ebooks)

```html
<!-- Embed PDF in modal -->
<iframe
    src="/api/ebooks/{{ ebook.id }}/pdf"
    width="100%"
    height="600"
    frameborder="0">
</iframe>
```

### KDP Export Buttons

```html
<!-- Preview button (DRAFT or APPROVED) -->
<button onclick="previewKDP({{ ebook.id }})">
    Aperçu KDP
</button>

<!-- Download button (APPROVED only) -->
<a href="/api/ebooks/{{ ebook.id }}/export-kdp" download>
    Télécharger KDP
</a>
```

### JavaScript Preview Handler

```javascript
function previewKDP(ebookId) {
    // Load KDP preview in iframe
    document.getElementById('pdfContainer').innerHTML = `
        <iframe
            src="/api/ebooks/${ebookId}/export-kdp?preview=true"
            width="100%"
            height="600">
        </iframe>
    `;
}
```

## KDP Specifications

### Default Configuration

```python
@dataclass
class KDPExportConfig:
    trim_size: tuple[float, float] = (8.0, 10.0)  # inches
    bleed_size: float = 0.125                      # inches (each side)
    paper_type: str = "premium_color"              # or "standard_color"
    include_barcode: bool = True
    cover_finish: str = "glossy"
    icc_rgb_profile: str = "sRGB_v4_ICC"
    icc_cmyk_profile: str = "USWebCoatedSWOP"
```

### Paper Type Auto-Adjustment

- **Premium Color**: Requires 24-828 pages
- **Standard Color**: For books < 24 pages
- System auto-switches if page count < 24

### Cover Assembly

```
[Back Cover] + [Spine] + [Front Cover]
```

- **Back Cover**: Line art (no text)
- **Spine**: Auto-calculated based on page count
- **Front Cover**: Colored with title

## Migration Notes

### Migrated From

- **Legacy endpoint PDF**: `GET /api/dashboard/ebooks/{id}/pdf` (dashboard.py)
- **Legacy endpoint KDP**: `GET /api/dashboard/ebooks/{id}/export-kdp` (dashboard.py)
- **Legacy use case KDP**: `src/backoffice/domain/usecases/export_to_kdp.py`

### Changes Made

1. **Added Event Emission**: Both use cases now emit domain events
2. **New Route Paths**: `/api/ebooks/{id}/...` (shorter, feature-based)
3. **Updated Frontend**: Templates now call new endpoints
4. **EventBus Integration**: ExportToKDPUseCase now accepts `event_bus` parameter

### Legacy Code Status

Both legacy endpoints in `dashboard.py` are commented out but kept for reference.

## Dependencies

### Internal
- `backoffice.domain.entities.ebook` - Ebook entity, KDPExportConfig
- `backoffice.domain.ports.ebook.ebook_port` - EbookPort interface
- `backoffice.domain.errors.error_taxonomy` - DomainError, ErrorCode
- `backoffice.infrastructure.providers.kdp_assembly_provider` - KDP PDF assembly
- `backoffice.infrastructure.providers.openrouter_image_provider` - Image processing
- `backoffice.features.shared.infrastructure.events.event_bus` - EventBus

### External
- `fastapi` - Web framework
- `weasyprint` (indirect) - PDF generation
- `pillow` (indirect) - Image processing

## Testing

### Unit Tests

Test use cases with fakes:
```python
from backoffice.features.ebook.export.domain.usecases.export_ebook_pdf import ExportEbookPdfUseCase

async def test_export_emits_event():
    event_bus = EventBus()
    events = []

    async def capture(event):
        events.append(event)

    event_bus.subscribe(EbookExportedEvent)(capture)

    use_case = ExportEbookPdfUseCase(fake_repo, event_bus)
    await use_case.execute(ebook_id=123)

    assert len(events) == 1
    assert events[0].ebook_id == 123
```

### Integration Tests

Test routes with real database:
```python
async def test_export_pdf_endpoint(client: AsyncClient):
    response = await client.get("/api/ebooks/123/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline" in response.headers["content-disposition"]
```

## Future Improvements

- [ ] Add bulk export (multiple ebooks at once)
- [ ] Add export queue (async generation)
- [ ] Add export templates (custom KDP configurations)
- [ ] Add watermarking for preview mode
- [ ] Add export history tracking
- [ ] Add export analytics dashboard
- [ ] Support other formats (EPUB, MOBI)
