# Instruction: Migrate HTMX/Jinja2 to React SPA with Hexagonal Architecture

## Feature

- **Summary**: Full migration from HTMX+Jinja2+Bootstrap server-side rendering to a React SPA with Green Design UI/UX. Frontend follows hexagonal architecture (ports/adapters) with Chicago-style testing (fakes over mocks). All 7 existing features preserved.
- **Stack**: `React 19, Vite 6, TypeScript 5, Redux Toolkit 2 (thunk.extraArgument gateways + listenerMiddleware), React Router 7, Tailwind CSS 4, Vitest 3`

## Existing files

### Backend routes to add JSON alternatives

- @src/backoffice/features/ebook/listing/presentation/routes/__init__.py (GET /api/dashboard/ebooks → HTML, has .json variant already)
- @src/backoffice/features/ebook/lifecycle/presentation/routes/__init__.py (GET /stats, PUT approve/reject → HTML only)
- @src/backoffice/features/ebook/creation/presentation/routes/__init__.py (POST /api/ebooks → HTML only)
- @src/backoffice/features/ebook/creation/presentation/routes/form_routes.py (GET /ebooks/new → HTML only, but /form-config exists as JSON)
- @src/backoffice/main.py (SPA serving, WebSocket endpoints, CORS config)

### Backend routes already JSON-ready (no changes needed)

- @src/backoffice/features/ebook/regeneration/presentation/routes/page_routes.py
- @src/backoffice/features/ebook/regeneration/presentation/routes/cover_routes.py
- @src/backoffice/features/ebook/export/presentation/routes/__init__.py
- @src/backoffice/features/ebook/pipeline/presentation/routes/pipeline_api.py

### New files to create

- frontend/ (entire React SPA project - structure below)

```
frontend/
├── src/
│   ├── app/
│   │   ├── store.ts                    # configureStore + listenerMiddleware
│   │   ├── router.tsx                  # React Router config
│   │   ├── App.tsx                     # Root component with layout
│   │   └── hooks.ts                    # useAppDispatch, useAppSelector
│   ├── features/
│   │   ├── ebooks/
│   │   │   ├── domain/
│   │   │   │   ├── entities/           # Ebook, PageMeta, Pagination types
│   │   │   │   ├── ports/             # EbookGateway, ExportGateway interfaces
│   │   │   │   └── usecases/          # createAsyncThunk use cases (receive gateways via extra)
│   │   │   ├── infrastructure/
│   │   │   │   ├── gateways/          # HttpEbookGateway (implements ports, injected via thunk.extraArgument)
│   │   │   │   └── middleware/        # listenerMiddleware for WebSocket progress
│   │   │   ├── store/
│   │   │   │   ├── slices/            # ebookSlice, regenerationSlice
│   │   │   │   └── selectors/         # selectEbooks, selectStats, selectProgress (unit tested)
│   │   │   ├── presentation/
│   │   │   │   ├── pages/             # DashboardPage, EbookDetailPage
│   │   │   │   └── components/        # EbookTable, StatsCards, CreateForm, EditModal, ProgressBar
│   │   │   └── tests/
│   │   │       └── unit/
│   │   │           ├── usecases/      # Chicago-style tests with fakes
│   │   │           └── selectors/     # Selector unit tests
│   │   └── pipelines/
│   │       ├── domain/
│   │       │   ├── entities/
│   │       │   ├── ports/
│   │       │   └── usecases/
│   │       ├── infrastructure/
│   │       │   ├── gateways/
│   │       │   └── middleware/
│   │       ├── store/
│   │       │   ├── slices/
│   │       │   └── selectors/
│   │       ├── presentation/
│   │       │   ├── pages/
│   │       │   └── components/
│   │       └── tests/
│   │           └── unit/
│   ├── shared/
│   │   ├── components/               # Layout, Sidebar, Modal, Toast, ConfirmDialog, ProgressBar
│   │   ├── hooks/                    # useWebSocket, useFileDownload
│   │   └── styles/                   # Tailwind theme (green-design tokens)
│   └── tests/
│       └── fakes/                    # Shared fake gateway implementations for testing
├── public/
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── vitest.config.ts
└── package.json
```

## Implementation phases

### Phase 1: Project Scaffolding & Green Design System

> Initialize React project with full toolchain and design tokens

1. Create Vite React-TS project in `frontend/`
2. Install dependencies: RTK, React Router, Tailwind CSS (no RTK Query — gateways handle API calls)
3. Configure Tailwind with Green Design palette (earth tones, natural greens, warm neutrals)
4. Setup `configureStore` with `thunk.extraArgument` (gateway injection) + `listenerMiddleware` (WebSocket side-effects)
5. Setup React Router with route skeleton (/, /ebooks/:id, /pipelines, /pipelines/:id)
6. Create shared layout: Sidebar + main content area
7. Create shared components: Toast, Modal, ConfirmDialog, StatusBadge, ProgressBar
8. Configure Vitest for unit testing
9. Add `useAppSelector` / `useAppDispatch` typed hooks

### Phase 2: Backend API Adaptation

> Add JSON endpoints alongside HTML ones for React consumption

1. `GET /api/ebooks` → JSON listing with pagination (reuse existing `.json` endpoint, move to primary path)
2. `GET /api/ebooks/{id}` → JSON detail with pages_meta (without base64 image_data for performance)
3. `GET /api/ebooks/{id}/pages` → JSON paginated page thumbnails (lazy load base64)
4. `GET /api/stats` → JSON `{draft: N, approved: N, rejected: N}`
5. `PUT /api/ebooks/{id}/approve` → JSON `{id, status, ...ebook_data}`
6. `PUT /api/ebooks/{id}/reject` → JSON `{id, status, ...ebook_data}`
7. `POST /api/ebooks` → accept JSON body (not form-data), return JSON `{id, title, status}`
8. Keep existing HTML endpoints untouched (backward compatibility during migration)

### Phase 3: Ebook Feature - Domain & Store Layer

> Hexagonal domain: entities, ports, use cases, selectors

1. Define TypeScript entities: `Ebook`, `PageMeta`, `PaginatedResult`, `Stats`, `FormConfig`
2. Define gateway ports (interfaces): `EbookGateway` (list, getById, create, approve, reject), `ExportGateway` (downloadPdf, exportKdp)
3. Implement `HttpEbookGateway` and `HttpExportGateway` (concrete adapters using fetch)
4. Implement use cases as `createAsyncThunk` receiving gateways via `thunkAPI.extra`: `listEbooks`, `createEbook`, `approveEbook`, `rejectEbook`, `getEbookDetail`
5. Create Redux slices: `ebookSlice` (ebooks, stats, filters, pagination), `regenerationSlice` (progress, modal state)
6. Create selectors: `selectEbooks`, `selectPagination`, `selectStats`, `selectCurrentEbook`, `selectProgress`
7. Create `FakeEbookGateway` and `FakeExportGateway` for testing
8. Write unit tests for use cases with fake gateways (Chicago-style): create store with fake extra, dispatch thunk, assert state via selectors
9. Write unit tests for selectors

### Phase 4: Dashboard & Listing UI

> React components consuming selectors only

1. `DashboardPage` — layout with stats + table + create button
2. `StatsCards` — draft/approved/rejected counts from `selectStats`
3. `EbookTable` — paginated table with status badges from `selectEbooks`
4. `PaginationControls` — page navigation from `selectPagination`
5. `StatusFilter` — filter tabs (All/Draft/Approved/Rejected)
6. `CreateEbookModal` — form with theme/audience dropdowns (loaded via gateway thunk), dispatches `createEbook` thunk
7. Approve/Reject buttons on table rows with `ConfirmDialog` for reject

### Phase 5: Ebook Detail & Regeneration UI

> Detail page with page grid, edit modal, WebSocket progress

1. `EbookDetailPage` — header (title, status, actions) + page grid
2. `PageGrid` — lazy-loaded thumbnails (fetch base64 on-demand per page via gateway thunk)
3. `PageEditModal` — preview image, custom prompt input, regenerate/edit/apply buttons
4. `CoverEditModal` — same pattern for cover
5. `ProgressBar` — percentage display from `selectProgress` selector
6. RTK `listenerMiddleware`: open WebSocket on regeneration start, dispatch progress actions to store, close on finish
7. Export actions: download PDF, export KDP (full/interior), preview KDP cover — file download via hidden anchor
8. Add/Complete pages actions from detail page

### Phase 6: Pipeline Feature

> Full pipeline CRUD with real-time progress

1. Define pipeline entities: `Pipeline`, `PipelinePage`, `PipelineStatus`
2. Define ports: `PipelineRepositoryPort` (list, create, getById, retry, cancel)
3. Implement use cases: `CreatePipelineUseCase`, `RetryPageUseCase`
4. Implement `HttpPipelineGateway` + `FakePipelineGateway`
5. Pipeline selectors: `selectPipelines`, `selectCurrentPipeline`, `selectPipelineProgress`
6. `PipelineListPage` — table of pipelines with status badges
7. `PipelineDetailPage` — status flow visualization, page list with retry buttons
8. `listenerMiddleware` for pipeline WebSocket progress
9. Unit tests for use cases and selectors

### Phase 7: SPA Integration & Cleanup

> Serve React from FastAPI, remove HTMX

1. Update `main.py` to serve `frontend/dist/` at `/` (catch-all SPA route)
2. Move all `/api/dashboard/*` JSON endpoints to `/api/*` (clean API prefix)
3. Ensure auth cookie forwarded on API calls (same-origin, `credentials: 'include'`)
4. Add `make frontend-install`, `make frontend-dev`, `make frontend-build` to Makefile
5. Remove old Jinja2 templates, static CSS/JS, HTMX dependencies
6. Update CORS config if needed
7. Final E2E smoke test with React frontend

## Reviewed implementation

- [ ] Phase 1: Project Scaffolding & Green Design System
- [ ] Phase 2: Backend API Adaptation
- [ ] Phase 3: Ebook Feature - Domain & Store Layer
- [ ] Phase 4: Dashboard & Listing UI
- [ ] Phase 5: Ebook Detail & Regeneration UI
- [ ] Phase 6: Pipeline Feature
- [ ] Phase 7: SPA Integration & Cleanup

## Validation flow

1. `make frontend-dev` starts Vite dev server on port 3000
2. Navigate to dashboard → ebooks listed with pagination, stats visible
3. Create ebook via form → ebook appears in table, stats update
4. Click ebook row → detail page with page grid loads
5. Click edit on a page → modal opens, click regenerate → progress bar shows %, preview updates
6. Apply edit → page saved, grid refreshes
7. Approve ebook → status changes to APPROVED
8. Export KDP → PDF downloads
9. Create pipeline → pipeline appears in list with progress updates
10. `make test-frontend` → all unit tests pass (use cases + selectors)
11. `make frontend-build && make dev` → production build served by FastAPI at /

## Estimations

- Confidence: 8/10
  - Existing JSON endpoints for regeneration/pipeline/export reduce backend work
  - Hexagonal architecture well understood (mirrors backend)
  - RTK listenerMiddleware well-suited for WebSocket side-effects
  - Risk: base64 image payloads may cause performance issues (mitigated by lazy loading)
  - Risk: auth cookie flow between Vite dev server (port 3000) and FastAPI (port 8001) needs proxy config
