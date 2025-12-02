# Instruction: Add New Pages in Edit Mode

## Feature

- **Summary**: Allow users to add AI-generated coloring pages (1-N at a time) to an existing ebook in edit mode, inserted before back cover, using same theme/style/seed, with max 100 pages limit and partial addition support
- **Stack**: `Python 3.12`, `FastAPI`, `Jinja2`, `HTMX`, `SQLAlchemy`

## Existing files

- @src/backoffice/features/ebook/regeneration/domain/usecases/complete_ebook_pages.py
- @src/backoffice/features/ebook/regeneration/domain/usecases/regenerate_content_page.py
- @src/backoffice/features/ebook/regeneration/presentation/routes/__init__.py
- @src/backoffice/features/ebook/listing/presentation/templates/ebook_detail.html
- @src/backoffice/features/ebook/shared/domain/constants.py
- @config/business/limits.yaml

### New file to create

- src/backoffice/features/ebook/regeneration/domain/usecases/add_new_pages.py

## Implementation phases

### Phase 1: Update page limit constant

> Change MAX_PAGES from 30 to 100

1. Edit `config/business/limits.yaml` to set `max_pages: 100`
2. Verify `constants.py` loads this value correctly

### Phase 2: Create AddNewPagesUseCase

> Core logic for adding AI-generated pages

1. Create `add_new_pages.py` use case inspired by `complete_ebook_pages.py`
2. Accept parameters: `ebook_id`, `count` (number of pages to add)
3. Load ebook and validate DRAFT status
4. Calculate current page count and remaining capacity (100 - current)
5. If `count > remaining`: set `count = remaining` (partial addition)
6. For each page to add:
   - Build prompt using `build_page_prompt_from_yaml()` with ebook's theme
   - Generate page via `ContentPageGenerationService`
   - Insert page before back cover in `structure_json`
7. Update `page_count` on ebook entity
8. Rebuild PDF via `RegenerationService`
9. Return result with `pages_added` and `limit_reached` boolean

### Phase 3: Add API endpoint

> Expose use case via REST API

1. Add `POST /api/ebooks/{ebook_id}/add-pages` in `regeneration/routes/__init__.py`
2. Request body: `{ "count": int }` (default 1, max based on remaining capacity)
3. Response: `{ "success": bool, "pages_added": int, "total_pages": int, "message": str }`
4. If limit reached, include message "Maximum 100 pages atteint"

### Phase 4: Update UI

> Add controls in ebook detail page

1. In `ebook_detail.html`, add new section in regeneration card (DRAFT only)
2. Add number input field (min=1, max dynamically set to remaining capacity)
3. Add "Ajouter X pages" button
4. Show loader/spinner during generation (HTMX `hx-indicator`)
5. On success: reload page to show new pages
6. On partial addition: show toast message with limit info

## Reviewed implementation

- [x] Phase 1: Update page limit constant
- [x] Phase 2: Create AddNewPagesUseCase
- [x] Phase 3: Add API endpoint
- [x] Phase 4: Update UI

## Validation flow

1. Open an existing DRAFT ebook with ~25 pages
2. In edit mode, enter "5" in the add pages input
3. Click "Ajouter 5 pages"
4. Verify spinner appears during generation
5. Verify 5 new pages appear before back cover
6. Verify pages have same theme/style as existing pages
7. Test limit: set ebook to 97 pages, request +5, verify only 3 added + message

## Estimations

- **Confidence**: 9/10
  - ✅ Similar use case exists (`complete_ebook_pages.py`) - proven pattern
  - ✅ Page generation service already handles theme-based prompts
  - ✅ UI pattern exists in regeneration section
  - ❌ Minor risk: batch generation of many pages may be slow (mitigated by spinner)
- **Complexity**: Medium - reuses existing components, minimal new code
