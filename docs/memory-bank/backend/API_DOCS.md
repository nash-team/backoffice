# API Documentation

## Authentication & Authorization

- **Authentication**: Google OAuth 2.0 (OpenID Connect)
- **Session Management**: JWT tokens stored in HTTP-only cookies (30 days)
- **Authorization**: Whitelist-based email verification (@config/auth/allowed_emails.yaml)
- **Protected Routes**: All routes except `/login`, `/auth/*`, `/static/*`, `/healthz`
- **Cookie Name**: `backoffice_session`

## Endpoints

- **Routes Location**: @src/backoffice/features/*/presentation/routes/
- **Base URL**: http://127.0.0.1:8001
- **API Docs**: http://127.0.0.1:8001/docs
- **Format**: REST + HTMX partials + JSON API (React SPA)
- **Protocol**: HTTP
- **Response Types**: JSON, HTML (Jinja2 templates), PDF, PNG

### Core Routes

#### Dashboard
- `GET /` - Main dashboard page (requires auth)
- `GET /healthz` - Health check endpoint (public)
- `POST /__test__/reset` - Reset DB for tests (TESTING env only)

### Authentication Routes

**Prefix**: None
**Tag**: auth
**Source**: @src/backoffice/features/auth/presentation/routes/__init__.py

- `GET /login` - Login page with error messages
- `GET /auth/google` - Initiate Google OAuth flow
- `GET /auth/google/callback` - Handle OAuth callback, validate email, set session cookie
- `POST /logout` - Clear session cookie, redirect to login

### Ebook Creation Routes

**Prefix**: `/api/ebooks`
**Tag**: Ebook Creation
**Source**: @src/backoffice/features/ebook/creation/presentation/routes/__init__.py

- `GET /api/ebooks/form-config` - Get themes (YAML) and audiences (JSON)
- `POST /api/ebooks` - Create new coloring book ebook
  - Form params: `ebook_type`, `theme_id`, `audience`, `title`, `author`, `number_of_pages`, `preview_mode`
  - Returns: HTML partial (updated ebooks table)
  - Emits: `EbookCreatedEvent`

**Prefix**: `/api/dashboard`
**Tag**: Ebook Creation Forms
**Source**: @src/backoffice/features/ebook/creation/presentation/routes/form_routes.py

- `GET /api/dashboard/ebooks/new` - Ebook creation form modal (HTML partial)

### Ebook Listing Routes

**Prefix**: `/api/dashboard`
**Tag**: Ebook Listing
**Source**: @src/backoffice/features/ebook/listing/presentation/routes/__init__.py

- `GET /api/dashboard/ebooks` - List ebooks with pagination (HTML partial)
  - Query params: `status` (draft|approved|rejected), `page`, `size`
- `GET /api/dashboard/ebooks.json` - List ebooks (JSON, for testing/API)
  - Query params: `status`, `page`, `size`
- `GET /api/dashboard/ebooks/{ebook_id}/preview` - Ebook preview modal (HTML partial)
- `GET /api/dashboard/ebooks/{ebook_id}` - Ebook detail page (full HTML)
- `GET /api/dashboard/drive/ebooks/{drive_id}` - Google Drive preview URL (text/plain)

### Ebook Lifecycle Routes

**Prefix**: `/api/dashboard`
**Tag**: Ebook Lifecycle
**Source**: @src/backoffice/features/ebook/lifecycle/presentation/routes/__init__.py

- `GET /api/dashboard/stats` - Ebook stats by status (HTML partial)
- `PUT /api/dashboard/ebooks/{ebook_id}/approve` - Approve ebook, upload to storage
  - Returns: HTML partial (updated table row)
  - Emits: `EbookApprovedEvent`
- `PUT /api/dashboard/ebooks/{ebook_id}/reject` - Reject ebook during review
  - Returns: HTML partial (updated table row)
  - Emits: `EbookRejectedEvent`

### Ebook Export Routes

**Prefix**: `/api/ebooks`
**Tag**: Ebook Export
**Source**: @src/backoffice/features/ebook/export/presentation/routes/__init__.py

- `GET /api/ebooks/{ebook_id}/pdf` - Export raw ebook PDF (inline disposition)
  - Emits: `EbookExportedEvent`
- `GET /api/ebooks/{ebook_id}/export-kdp` - Export KDP paperback PDF
  - Query param: `preview` (bool) - inline display vs attachment download
  - Requires: APPROVED status (unless preview=true allows DRAFT)
  - Emits: `KDPExportGeneratedEvent`
- `GET /api/ebooks/{ebook_id}/export-kdp/interior` - Export KDP interior/manuscript PDF
  - Query param: `preview` (bool)
  - Content: Pages only (no cover/back)
  - Emits: `KDPExportGeneratedEvent`
- `GET /api/ebooks/{ebook_id}/kdp-cover-preview` - KDP cover with template overlay (PNG)
  - Returns: Full cover (back + spine + front) with KDP template overlay for visual validation

### Ebook Regeneration Routes

**Prefix**: `/api/ebooks`
**Tag**: Ebook Regeneration
**Source**: @src/backoffice/features/ebook/regeneration/presentation/routes/__init__.py

#### General Regeneration
- `POST /api/ebooks/{ebook_id}/pages/regenerate` - Regenerate one or more pages
  - Body: `{"page_type": "cover|back_cover|content_page", "page_index": 0, "page_indices": [1,2,3]}`
  - Single page (backward compat): `page_index`
  - Multiple pages (content only): `page_indices` array
  - Returns: JSON with success status
- `POST /api/ebooks/{ebook_id}/complete-pages` - Add blank pages to reach KDP minimum (24)
  - Query param: `target_pages` (default: 24)
  - Returns: JSON with new page count
- `POST /api/ebooks/{ebook_id}/add-pages` - Add new AI-generated coloring pages
  - Body: `{"count": 5}`
  - Returns: JSON with pages_added, total_pages, limit_reached

#### Cover Regeneration
**Tag**: Cover Regeneration
**Source**: @src/backoffice/features/ebook/regeneration/presentation/routes/cover_routes.py

- `POST /api/ebooks/{ebook_id}/cover/preview-regenerate` - Preview regenerate cover (no save)
  - Body (optional): `{"current_image_base64": "...", "custom_prompt": "..."}`
  - Returns: JSON with base64 image (not saved to DB)
- `POST /api/ebooks/{ebook_id}/cover/edit` - Edit cover with targeted corrections (preview only)
  - Body: `{"edit_prompt": "replace 5 toes with 3 toes", "current_image_base64": "..."}`
  - Returns: JSON with base64 edited image (not saved)
- `POST /api/ebooks/{ebook_id}/cover/apply-edit` - Apply cover edit (save + rebuild PDF)
  - Body: `{"image_base64": "...", "prompt": "..."}`
  - Saves to DB, rebuilds PDF, resets APPROVED to DRAFT
  - Emits: `PageRegeneratedEvent`
  - Returns: JSON with success, ebook_id, preview_url

#### Page Regeneration
**Tag**: Page Regeneration
**Source**: @src/backoffice/features/ebook/regeneration/presentation/routes/page_routes.py

- `POST /api/ebooks/{ebook_id}/pages/{page_index}/preview-regenerate` - Preview regenerate page (no save)
  - Body (optional): `{"current_image_base64": "...", "custom_prompt": "..."}`
  - Returns: JSON with base64 image (not saved)
- `POST /api/ebooks/{ebook_id}/pages/{page_index}/edit` - Edit page with targeted corrections (preview only)
  - Body: `{"edit_prompt": "fix anatomy", "current_image_base64": "..."}`
  - Returns: JSON with base64 edited image (not saved)
- `POST /api/ebooks/{ebook_id}/pages/{page_index}/apply-edit` - Apply page edit (save + rebuild PDF)
  - Body: `{"image_base64": "...", "prompt": "..."}`
  - Saves to DB, rebuilds PDF, resets APPROVED to DRAFT
  - Emits: `PageRegeneratedEvent`
  - Returns: JSON with success, ebook_id, preview_url
- `GET /api/ebooks/{ebook_id}/pages/{page_index}/data` - Get page data (image + prompt)
  - Returns: JSON with image_base64, prompt, title (for on-demand loading)

### JSON API Routes (React SPA)

> Pure JSON endpoints for the React frontend. Coexist with HTMX routes above.

#### Ebook Listing JSON API

**Prefix**: `/api`
**Tag**: Ebook API
**Source**: @src/backoffice/features/ebook/listing/presentation/routes/api.py

- `GET /api/ebooks` - List ebooks (paginated JSON)
  - Query params: `status` (draft|approved|rejected), `page`, `size`
  - Returns: `{items, total, page, per_page, total_pages}`
- `GET /api/ebooks/{ebook_id}` - Ebook detail (JSON, includes `pages_meta` without base64 image_data)

#### Ebook Lifecycle JSON API

**Prefix**: `/api`
**Tag**: Ebook Lifecycle API
**Source**: @src/backoffice/features/ebook/lifecycle/presentation/routes/api.py

- `GET /api/stats` - Stats by status (JSON: `{draft, approved, rejected}`)
- `PUT /api/ebooks/{ebook_id}/approve` - Approve ebook (JSON response)
  - Emits: `EbookApprovedEvent`
- `PUT /api/ebooks/{ebook_id}/reject` - Reject ebook (JSON response)
  - Emits: `EbookRejectedEvent`

#### Ebook Creation JSON API

**Prefix**: `/api`
**Tag**: Ebook Creation API
**Source**: @src/backoffice/features/ebook/creation/presentation/routes/api.py

- `POST /api/ebooks` - Create coloring book (JSON body)
  - Body: `CreateEbookBody` - `{title?, theme, audience, num_pages=8, preview_mode=false}`
  - Returns: `{id, title, status, num_pages, created_at}`
  - Emits: `EbookCreatedEvent`

## Request/Response Formats

- **Request Body**: JSON (for POST/PUT), Form data (for multipart)
- **Response Formats**:
  - JSON (API endpoints, error responses)
  - HTML (Jinja2 templates, HTMX partials)
  - PDF (application/pdf with Content-Disposition headers)
  - PNG (image/png for KDP cover preview)
- **HTMX Integration**: Many endpoints return HTML partials with `HX-Trigger` headers
- **Error Responses**: JSON with `detail` field, appropriate HTTP status codes

## Middleware Stack

**Order** (first added = last executed on request):
1. `AuthMiddleware` - Session validation, redirects to /login
2. `SessionMiddleware` - OAuth state management (authlib)
3. `CORSMiddleware` - Environment-based CORS (dev: localhost, prod: configured domains)

## File Upload/Download

- **Storage**: Local filesystem (@src/backoffice/data/storage/) or Google Drive (optional)
- **PDF Cache**: Disabled (`Cache-Control: no-cache`) for fresh PDFs after regeneration
- **KDP Specs**: 8×10", 300 DPI, 0.125" bleed, 24-100 pages
- **Image Format**: PNG (base64 in structure_json, binary for PDF assembly)
