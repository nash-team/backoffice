# Backend Communication

## HTTP Client

- Native `fetch` API (no axios)
- `credentials: 'include'` on all requests (session cookies)
- Base URL: `/api` (relative, proxied in dev)
- `Content-Type: application/json` for POST/PUT
- `response.blob()` for PDF downloads

## Proxy Configuration

- Dev: Vite proxy `/api/*` → `http://localhost:8001` @frontend/vite.config.ts
- Prod: FastAPI serves frontend from `frontend/dist/`, no proxy needed
- WebSocket proxy enabled for progress updates

## Gateway → Endpoint Mapping

### EbookGateway

| Method | HTTP | Endpoint |
|--------|------|----------|
| `list(page, status?)` | GET | `/api/ebooks?page=N&status=X` |
| `getById(id)` | GET | `/api/ebooks/{id}` |
| `create(data)` | POST | `/api/ebooks` |
| `approve(id)` | PUT | `/api/ebooks/{id}/approve` |
| `reject(id)` | PUT | `/api/ebooks/{id}/reject` |
| `getStats()` | GET | `/api/stats` |
| `getFormConfig()` | GET | `/api/ebooks/form-config` |

### ExportGateway

| Method | HTTP | Endpoint |
|--------|------|----------|
| `downloadPdf(id)` | GET | `/api/ebooks/{id}/pdf` |
| `exportKdpInterior(id)` | GET | `/api/ebooks/{id}/export-kdp/interior` |
| `exportKdpCover(id)` | GET | `/api/ebooks/{id}/kdp-cover-preview` |
| `exportKdpFull(id)` | GET | `/api/ebooks/{id}/export-kdp` |

### RegenerationGateway

| Method | HTTP | Endpoint |
|--------|------|----------|
| `getPageData(id, idx)` | GET | `/api/ebooks/{id}/pages/{idx}/data` |
| `previewRegenerate(...)` | POST | `/api/ebooks/{id}/pages/{idx}/preview-regenerate` |
| `editPage(...)` | POST | `/api/ebooks/{id}/pages/{idx}/edit` |
| `applyEdit(...)` | POST | `/api/ebooks/{id}/pages/{idx}/apply-edit` |
| `previewRegenerateCover(...)` | POST | `/api/ebooks/{id}/cover/preview-regenerate` |
| `editCover(...)` | POST | `/api/ebooks/{id}/cover/edit` |
| `applyCoverEdit(...)` | POST | `/api/ebooks/{id}/cover/apply-edit` |

## Authentication

- Google OAuth session cookie (`backoffice_session`)
- `credentials: 'include'` on all fetch calls
- No token management in frontend (cookie-based)

## Error Handling

- Check `response.ok`, throw on failure
- Errors propagate to Redux `.rejected` → `state.error`
- No retry logic or interceptors

## Data Loading Strategy

- List: metadata only (no images)
- Detail: `pages_meta` without `image_data`
- Images: on-demand via `getPageData` (lazy loading)
- Exports: blob download via `useFileDownload` hook

## WebSocket

- Endpoint: `/api/ws/{clientId}` (proxied via Vite in dev)
- Hook: `useRegenWebSocket(ebookId)`
- Dispatches `setProgress({ status: number, currentStep: number, state: string })` to Redux
- `state`: `"running"` | `"finished"` — auto-disconnects on finished
- Used in `EbookDetailPage` and `PageEditModal` for regeneration progress
