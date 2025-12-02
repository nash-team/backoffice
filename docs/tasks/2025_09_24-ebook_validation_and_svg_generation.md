# Instruction: Strategic Implementation of Human Validation and SVG Generation

## Feature

- **Summary**: Implement human validation workflow for ebook quality control and SVG generation pipeline for coloring book pages to enhance ebook offerings with visual content
- **Stack**: `FastAPI 0.104+`, `SQLAlchemy 2.0+`, `PostgreSQL 16+`, `Alembic 1.13+`, `Bootstrap 5.3`, `HTMX 1.9`, `WeasyPrint`, `OpenAI API`, `Potrace (external)`, `Google Drive API`

## Existing files

- @src/backoffice/domain/entities/ebook.py
- @src/backoffice/infrastructure/models/ebook_model.py
- @src/backoffice/presentation/templates/dashboard.html
- @src/backoffice/presentation/routes/dashboard.py
- @src/backoffice/presentation/routes/ebook_routes.py
- @src/backoffice/infrastructure/adapters/repositories/ebook_repository.py
- @src/backoffice/domain/usecases/get_stats.py

### New file to create

- src/backoffice/domain/usecases/approve_ebook.py
- src/backoffice/domain/usecases/reject_ebook.py
- src/backoffice/infrastructure/adapters/openai_image_generator.py
- src/backoffice/infrastructure/adapters/potrace_vectorizer.py
- src/backoffice/domain/entities/image_page.py
- src/backoffice/presentation/templates/partials/validation_buttons.html

## Implementation phases

### Phase 1 - Human Validation System

> Enable binary approval workflow for complete PDF validation

1. Update EbookStatus enum with DRAFT, PENDING, APPROVED and REJECTED statuses
2. Create approve_ebook and reject_ebook use cases with proper business logic
3. Generate database migration for new status values
4. Add validation action buttons to dashboard ebooks table
5. Create HTMX endpoints for approve/reject actions with proper error handling
6. Update stats calculation to include approved/rejected counts
7. Write comprehensive unit tests for validation use cases
8. Add E2E tests for complete validation workflow

### Phase 2 - SVG Generation Infrastructure

> Build AI image generation to SVG vectorization pipeline

1. Create OpenAI image generation adapter with proper error handling and rate limiting
2. Implement Potrace vectorization service adapter with fallback to PNG conversion
3. Design ImagePage entity with full-page layout specifications
4. Extend ebook structure to support dedicated image pages and cover enhancement
5. Update WeasyPrint templates for full-bleed SVG rendering
6. Create user interface for URL input and SVG preview
7. Integrate SVG generation into existing ebook creation workflow
8. Add comprehensive tests for image generation pipeline

## Reviewed implementation

- [ ] Phase 1
- [ ] Phase 2

## Validation flow

1. Navigate to backoffice dashboard and authenticate
2. Create new ebook with mixed content type (story + coloring pages)
3. Input story prompt and provide image URLs for coloring pages
4. Generate ebook and verify PDF contains both text and SVG pages
5. Validate ebook shows PENDING status with approve/reject buttons
6. Click approve button and verify status changes to APPROVED
7. Create another ebook and reject it, verify REJECTED status
8. Test filtering by status works correctly
9. Verify stats show correct counts for all status types

## Estimations

- High confidence (9/10) - leveraging existing architecture patterns
- Time to implement: 7-10 days (Phase 1: 2-3 days, Phase 2: 5-7 days)
