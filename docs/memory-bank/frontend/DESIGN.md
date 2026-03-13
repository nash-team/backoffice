# Design

## Styling

- **Framework**: Tailwind CSS 4 (Vite plugin)
- **Approach**: Utility-first, no CSS modules, no scoped styles
- **Theme**: Custom colors in `@frontend/src/shared/styles/theme.css` via `@theme` block
- **Responsive**: `sm:`, `md:`, `lg:` breakpoints

## Color Palette

| Token | Usage | Values |
|-------|-------|--------|
| `primary-*` | Forest greens | #22c55e -> #052e16 |
| `neutral-*` | Warm stone grays | UI backgrounds/text |
| `status-draft` | Draft badge | Gray |
| `status-approved` | Approved badge | Green |
| `status-rejected` | Rejected badge | Red |
| `status-processing` | Processing badge | Blue |
| `sidebar-*` | Sidebar dark green | #166534 |

## Layout

- Two-column: fixed `Sidebar` + scrollable main content
- `AppLayout` wraps all routes with `<Outlet />`

## Shared Components

| Component | Pattern | Notes |
|-----------|---------|-------|
| `Modal` | Native `<dialog>` + ref | `.showModal()` / `.close()` |
| `Toast` | CustomEvent-based | `showToast(type, text)`, auto-dismiss 4s |
| `ProgressBar` | Step-based progress | Regeneration progress |
| `Sidebar` | Fixed nav | App navigation |
| `AppLayout` | Layout wrapper | Sidebar + Outlet |

## Feature Components

| Component | Purpose |
|-----------|---------|
| `CreateEbookModal` | Form modal for new ebook |
| `EbookTable` | Paginated ebook list with actions |
| `PageGrid` | Thumbnail grid of ebook pages (lazy image loading via thunks) |
| `PageEditModal` | Image editing (regenerate/correct modes, circular spinner + %, undo via `restorePreview`) |
| `PaginationControls` | Page navigation with ellipsis truncation |
| `ActionToolbar` | Export dropdown + approve/reject actions |
| `KdpCoverPreviewModal` | KDP cover preview with template overlay |

## Pages

| Page | Route | Content |
|------|-------|---------|
| `DashboardPage` | `/` | EbookTable + Pagination + CreateEbookModal |
| `EbookDetailPage` | `/ebooks/:id` | Metadata + PageGrid + PageEditModal + ActionToolbar |

## Component Composition

```
DashboardPage
├── EbookTable
├── PaginationControls
└── CreateEbookModal
    └── Modal (shared)
```

## Props Pattern

- Functional components only
- Props destructured in signature
- Named exports (no default exports)
- Interface per component: `interface ComponentProps { ... }`
