<!--  AI INSTRUCTIONS ONLY -- Follow those rules, do not output them.

- ENGLISH ONLY
- Text is straight to the point, no emojis, no style, use bullet points.
- Replace placeholders (`{variables}`) with actual user inputs.
- Define flow of the feature, from start to end.
- Interpret comments on this file to help you fill it.
-->

# Instruction: Page Edit Modal with Regeneration

## Feature

- **Summary**: Fix the edit modal flow so preview regenerations and apply always use the image currently shown in the modal (latest preview/saved version), never the PDF original, and nothing is saved until “Apply” is clicked.
- **Stack**: [FastAPI 0.104+, Jinja2 3.1+, HTMX 1.9+, Bootstrap 5.3, SQLAlchemy 2.0+, Python 3.11+]

## Existing files

- @src/backoffice/features/ebook/regeneration/presentation/routes/__init__.py
- @src/backoffice/features/ebook/regeneration/domain/usecases/regenerate_content_page.py
- @src/backoffice/features/ebook/regeneration/domain/services/regeneration_service.py
- @src/backoffice/features/ebook/listing/presentation/templates/ebook_detail.html
- @src/backoffice/features/ebook/shared/domain/services/page_generation.py
- @src/backoffice/features/ebook/shared/infrastructure/repositories/ebook_repository.py

### New file to create

- None (adjust existing preview/apply flow and modal wiring)

## Implementation phases

### Phase 1: Preview regeneration uses modal image

> Ensure preview regeneration chains from the image currently in the modal, not the PDF snapshot.

1. Update preview use case/endpoint to accept and use the modal’s current image (latest preview) as input while keeping prompt/theme loading and random seed.
2. Keep validations (DRAFT-only, valid page index); still no DB/storage/PDF writes.
3. Adjust/add tests to cover chaining from current preview, invalid page index, non-DRAFT ebook, and prompt reuse.

### Phase 2: Modal wiring enforces chaining

> Guarantee the UI sends the current modal image for each regeneration and keeps unsaved previews in-modal.

1. Update modal HTMX/JS to pass the latest preview image back on each regenerate call.
2. Keep modal open across regenerations with spinner + error handling; Cancel still discards unsaved previews.
3. Ensure Apply sends the last modal preview, never the PDF image.

### Phase 3: Apply persists last preview

> Persist exactly the image last shown in the modal.

1. Update apply use case to consume the modal-provided preview, update structure_json, rebuild/upload PDF, reset APPROVED→DRAFT if needed, emit regeneration event, and save.
2. Keep error handling for invalid ebook/page.
3. Adjust/add tests to confirm apply uses the modal preview, saves correctly, resets status, and emits events.

## Reviewed implementation

<!-- That section is filled by a review agent that ensures feature has been properly implemented -->

- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3

## Validation flow

<!-- What would a REAL user do to 100% validate the feature? -->

1. Open a DRAFT ebook detail page and click Edit on a content page.
2. See modal with current page image sourced from latest saved version.
3. Click Regenerate; spinner shows; preview updates with new image derived from the current modal image (not the PDF snapshot).
4. Regenerate multiple times; confirm each preview replaces the last and chains from the current modal preview.
5. Click Cancel and confirm no change persisted; reopen Edit shows original saved page.
6. Regenerate again, click Apply; modal closes; toast confirms update; page reloads with updated PDF page.
7. Reopen Edit to confirm modal now shows the newly saved image as the new base for further regenerations.
8. Try a non-DRAFT ebook or invalid page index and verify proper error response.

## Estimations

- Confidence: 9/10 (clear flow, existing regeneration services; watch base64 size and concurrent edits)
- Time to implement: 4–6 hours
