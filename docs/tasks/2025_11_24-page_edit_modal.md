# Instruction: Page Edit Modal with Regeneration

## Feature

- **Summary**: Allow users to regenerate a page multiple times in a modal until satisfied, without rebuilding the entire PDF. User clicks "Edit" button on any content page, modal opens with image preview, user can regenerate with same prompt (new seed), and apply changes only when satisfied.
- **Stack**: `FastAPI 0.104+`, `Jinja2 3.1+`, `HTMX 1.9+`, `Bootstrap 5.3`, `SQLAlchemy 2.0+`, `Python 3.11+`

## Existing files

- `src/backoffice/features/ebook/regeneration/presentation/routes/__init__.py` (existing regeneration API)
- `src/backoffice/features/ebook/regeneration/domain/usecases/regenerate_content_page.py` (existing use case)
- `src/backoffice/features/ebook/regeneration/domain/services/regeneration_service.py` (shared service)
- `src/backoffice/features/ebook/listing/presentation/templates/ebook_detail.html` (page with regeneration buttons)
- `src/backoffice/features/ebook/shared/domain/services/page_generation.py` (page generation service)
- `src/backoffice/features/ebook/shared/infrastructure/repositories/ebook_repository.py` (ebook persistence)

### New files to create

- `src/backoffice/features/ebook/regeneration/domain/usecases/preview_regenerate_page.py` (preview regeneration without DB save)
- `src/backoffice/features/ebook/regeneration/domain/usecases/apply_page_edit.py` (save preview to DB and rebuild PDF)
- `src/backoffice/features/ebook/regeneration/presentation/templates/partials/edit_page_modal.html` (modal UI)
- `src/backoffice/features/ebook/regeneration/tests/unit/domain/usecases/test_preview_regenerate_page.py` (unit tests for preview)
- `src/backoffice/features/ebook/regeneration/tests/unit/domain/usecases/test_apply_page_edit.py` (unit tests for apply)

## Implementation phases

### Phase 1: Backend - Preview Regeneration Endpoint

> Create API endpoint that regenerates a page without saving to DB or storage (preview mode)

1. Create `PreviewRegeneratePageUseCase` in `domain/usecases/preview_regenerate_page.py`
   - Validate ebook exists and is DRAFT status
   - Validate page_index is valid content page
   - Load theme and workflow params from YAML
   - Generate new image using `ContentPageGenerationService` with random seed
   - Return image as base64 (no DB/storage save)
   - No PDF rebuild, no status change
2. Add POST endpoint `/api/ebooks/{ebook_id}/pages/{page_index}/preview-regenerate` in `presentation/routes/__init__.py`
   - Inject dependencies (ebook_repo, page_service, theme_repo)
   - Call `PreviewRegeneratePageUseCase.execute()`
   - Return JSON with `{"success": true, "image_base64": "...", "page_index": N}`
   - Handle errors (404 if ebook not found, 400 if invalid status/page)
3. Write unit tests in `tests/unit/domain/usecases/test_preview_regenerate_page.py`
   - Use `FakeEbookRepository` and `FakeContentPagePort`
   - Test: preview generates new image without DB save
   - Test: fails if ebook not DRAFT
   - Test: fails if invalid page_index
   - Test: uses same prompt as original generation

### Phase 2: Frontend - Edit Modal UI

> Create modal interface with image preview and regeneration controls

1. Create modal template `presentation/templates/partials/edit_page_modal.html`
   - Bootstrap 5 modal structure
   - Image preview element (updates via HTMX)
   - "Regenerate" button with HTMX to preview endpoint
   - "Apply" button (saves changes)
   - "Cancel" button (closes modal without saving)
   - Loading spinner during regeneration
   - Error message display area
2. Add "Edit" button to each content page in `ebook_detail.html`
   - Add button next to existing page checkboxes (lines 282-296)
   - Use HTMX `hx-get` to load modal template with page data
   - Button triggers modal open with current page image and page_index
   - Only show for DRAFT ebooks (same condition as regeneration section)
3. Implement HTMX interactions in modal
   - "Regenerate" button: `hx-post` to preview endpoint, swap image on success
   - Show spinner during generation
   - Display error toast if generation fails
   - Keep modal open between regenerations
   - "Cancel" dismisses modal (Bootstrap data-bs-dismiss)
4. Add JavaScript helper for modal management in `static/js/dashboard.js`
   - Function to open modal with page_index
   - Function to handle image swap after regeneration
   - Function to pass image_base64 to apply endpoint

### Phase 3: Backend - Apply Edit Endpoint

> Save preview image to DB and rebuild PDF when user clicks Apply

1. Create `ApplyPageEditUseCase` in `domain/usecases/apply_page_edit.py`
   - Validate ebook exists and is DRAFT status
   - Receive image_base64 and page_index from request
   - Decode base64 to bytes
   - Update `structure_json.pages_meta[page_index]` with new image
   - Use `RegenerationService.rebuild_and_upload_pdf()` to reassemble PDF
   - If ebook was APPROVED, reset to DRAFT
   - Save ebook to DB
   - Emit `ContentPageRegeneratedEvent` (reuse existing event)
2. Add POST endpoint `/api/ebooks/{ebook_id}/pages/{page_index}/apply-edit` in `presentation/routes/__init__.py`
   - Receive JSON body: `{"image_base64": "...", "page_index": N}`
   - Call `ApplyPageEditUseCase.execute()`
   - Return JSON with `{"success": true, "message": "Page updated", "preview_url": "..."}`
   - Handle errors (400 if invalid data, 500 if save fails)
3. Wire "Apply" button in modal to apply endpoint
   - HTMX `hx-post` to apply endpoint with image_base64 from preview
   - On success: show toast, close modal, reload page to show updated PDF
   - On error: show error toast, keep modal open
4. Write unit tests in `tests/unit/domain/usecases/test_apply_page_edit.py`
   - Use `FakeEbookRepository` and `FakeFileStorage`
   - Test: apply saves image to DB and rebuilds PDF
   - Test: reset APPROVED ebook to DRAFT
   - Test: fails if ebook not found
   - Test: emits ContentPageRegeneratedEvent

## Reviewed implementation

- [ ] Phase 1: Backend - Preview Regeneration Endpoint
- [ ] Phase 2: Frontend - Edit Modal UI
- [ ] Phase 3: Backend - Apply Edit Endpoint

## Validation flow

1. Navigate to ebook detail page for a DRAFT ebook
2. Click "Edit" button on a content page (e.g., Page 1)
3. Modal opens showing current page image
4. Click "Regenerate" button
5. Image updates in modal with new generation (spinner shown during loading)
6. Click "Regenerate" again to try another variation
7. Image updates again (can iterate multiple times)
8. Click "Apply" to save changes
9. Modal closes, toast confirms "Page updated"
10. Page reloads and PDF viewer shows updated page
11. Click "Edit" again and verify modal shows the new saved image
12. Click "Cancel" in modal and verify no changes are saved

## Estimations

- **Confidence**: 9/10
  - ✅ Architecture is well-defined (feature-based, DDD)
  - ✅ Regeneration logic already exists (reusable services)
  - ✅ HTMX + Bootstrap 5 already in use (coherent stack)
  - ✅ Test infrastructure ready (fakes, co-localized tests)
  - ✅ Clear separation: preview (no save) vs apply (save + rebuild)
  - ❌ Minor risk: Handling large base64 images in JSON (mitigated by using efficient encoding)
- **Time to implement**: 4-6 hours
  - Phase 1 (Backend Preview): 1.5 hours (use case + endpoint + tests)
  - Phase 2 (Frontend Modal): 2 hours (template + HTMX wiring + styling)
  - Phase 3 (Backend Apply): 1.5 hours (use case + endpoint + tests)
  - Testing & refinement: 1 hour
