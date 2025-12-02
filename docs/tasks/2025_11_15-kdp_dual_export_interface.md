# Instruction: KDP Dual Export Interface - Cover and Interior Separation

## Feature

- **Summary**: Enable KDP publishers to download and preview Cover and Interior PDFs separately, and automatically upload both files to Google Drive upon approval (instead of a single full book PDF).
- **Stack**: `Python 3.12`, `FastAPI 0`, `SQLAlchemy 2`, `Jinja2 3`, `HTMX 2`, `PostgreSQL 16`, `Google Drive API v3`, `Alembic 1`

## Existing files

- @src/backoffice/features/ebook/lifecycle/domain/usecases/approve_ebook_usecase.py
- @src/backoffice/features/ebook/shared/domain/ports/file_storage_port.py
- @src/backoffice/features/ebook/shared/infrastructure/adapters/google_drive_storage_adapter.py
- @src/backoffice/features/ebook/shared/domain/entities/ebook.py
- @src/backoffice/features/ebook/shared/infrastructure/models/ebook_model.py
- @src/backoffice/features/ebook/listing/presentation/templates/partials/ebook_preview_modal.html
- @src/backoffice/features/ebook/export/presentation/routes/__init__.py
- @src/backoffice/features/ebook/export/domain/usecases/export_to_kdp.py
- @src/backoffice/features/ebook/export/domain/usecases/export_to_kdp_interior.py

### New files to create

- Migration file for adding `drive_id_cover` and `drive_id_interior` columns to ebooks table

## Implementation phases

### Phase 1: Database schema update

> Add storage for separate Drive IDs (Cover and Interior)

1. Add `drive_id_cover: str | None` and `drive_id_interior: str | None` fields to `Ebook` entity
2. Add corresponding nullable columns to `EbookModel` SQLAlchemy model
3. Create Alembic migration for adding both columns to `ebooks` table
4. Run migration to update schema

### Phase 2: Modify approval workflow for dual upload

> Change ApproveEbookUseCase to upload Cover + Interior separately to Drive

1. Update `ApproveEbookUseCase.execute()` to generate Cover KDP PDF using `ExportToKDPUseCase`
2. Generate Interior KDP PDF using `ExportToKDPInteriorUseCase`
3. Upload Cover PDF to Drive with filename `{title}_Cover_KDP.pdf` via `file_storage.upload_ebook()`
4. Upload Interior PDF to Drive with filename `{title}_Interior_KDP.pdf`
5. Store both Drive IDs in ebook entity (`drive_id_cover`, `drive_id_interior`)
6. Update approval success message to reflect dual upload
7. Remove or deprecate old `drive_id` field (keep temporarily for backward compatibility)

### Phase 3: Add KDP download buttons to UI

> Expose Cover and Interior download buttons (visible in DRAFT and APPROVED)

1. Add "Télécharger Cover KDP" button in `ebook_preview_modal.html` action buttons section
2. Link button to `/api/ebooks/{ebook.id}/export-kdp` (download mode, no preview param)
3. Show button for both DRAFT and APPROVED status
4. Add "Télécharger Interior KDP" button next to Cover button
5. Link to `/api/ebooks/{ebook.id}/export-kdp/interior` (download mode)
6. Ensure proper Bootstrap styling and icons (e.g., `fa-file-download`)

### Phase 4: Add Interior preview functionality

> Allow users to preview Interior PDF before approval (like Cover preview)

1. Add "Aperçu Interior KDP" button in `ebook_preview_modal.html` (visible DRAFT + APPROVED)
2. Create JavaScript function `showKDPInteriorPreview(ebookId)` similar to existing `showKDPPreview()`
3. Replace PDF viewer container with iframe loading `/api/ebooks/{ebookId}/export-kdp/interior?preview=true`
4. Display loading spinner while Interior PDF generates
5. No overlay template needed (unlike Cover, Interior has no visual validation template)

## Reviewed implementation

- [ ] Phase 1: Database schema updated with Cover and Interior Drive IDs
- [ ] Phase 2: Approval uploads 2 KDP files to Drive
- [ ] Phase 3: Cover and Interior download buttons visible and functional
- [ ] Phase 4: Interior preview works in DRAFT and APPROVED

## Validation flow

1. Create new ebook via dashboard form → wait for generation completion
2. Click "Preview" on DRAFT ebook → modal opens with PDF viewer
3. Click "Aperçu Cover KDP" → Cover preview with overlay template displays
4. Click "Aperçu Interior KDP" → Interior pages preview displays (no overlay)
5. Click "Télécharger Cover KDP" → `{Title}_Cover_KDP.pdf` downloads
6. Click "Télécharger Interior KDP" → `{Title}_Interior_KDP.pdf` downloads
7. Click "Approuver" → Success message shows "2 fichiers uploadés sur Drive"
8. Check Google Drive → Verify both `{Title}_Cover_KDP.pdf` and `{Title}_Interior_KDP.pdf` exist
9. Verify ebook status changed to APPROVED
10. Open APPROVED ebook modal → Download buttons still visible and functional

## Estimations

- **Confidence**: 9/10
  - ✅ All backend routes already exist (Cover and Interior exports)
  - ✅ Use cases are fully implemented and tested
  - ✅ Drive upload logic is proven and working
  - ✅ Frontend patterns are well-established (HTMX + JS functions)
  - ✅ Database migration is straightforward (2 nullable columns)
  - ❌ Minor risk: Drive upload might timeout if both files are large (mitigation: sequential uploads)
  - ❌ Minor risk: Migration needs careful testing with existing ebooks

- **Time to implement**: 2-3 hours
  - Phase 1 (DB schema): 30 min (migration + entity update)
  - Phase 2 (Approval workflow): 60 min (dual upload logic + Drive integration)
  - Phase 3 (Download buttons): 20 min (HTML + styling)
  - Phase 4 (Interior preview): 20 min (JS function + iframe)
  - Testing & validation: 30 min (E2E workflow test)
