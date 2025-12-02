# Instruction: Square Format for Coloring Ebooks with KDP Print Quality

## Feature

- **Summary**: Convert coloring ebook page format from A4 to 8.5" x 8.5" square with KDP-compliant margins and 300+ DPI image quality for commercial printing
- **Stack**: `Python 3.11`, `WeasyPrint 61.0+`, `PIL/Pillow 10.0+`, `FastAPI`, `SQLAlchemy 2.0`, `OpenAI API`, `CSS3`

## Existing files

- @src/backoffice/domain/entities/ebook.py
- @src/backoffice/domain/services/pdf_renderer.py
- @src/backoffice/infrastructure/adapters/pdf_generator_adapter.py
- @src/backoffice/presentation/templates/pages/images/coloring_page.html
- @src/backoffice/presentation/templates/pages/covers/cover_coloring.html
- @src/backoffice/infrastructure/adapters/openai_image_generator.py

### New file to create

- src/backoffice/domain/constants/page_formats.py

## Implementation phases

### Phase 1: Configuration and Constants

> Establish square format specifications and DPI requirements

1. Create page_formats.py with 8.5" square dimensions, KDP margins (0.5" outer, 0.75" inner), and 300 DPI constants
2. Add PageFormat enumeration (SQUARE_8_5, A4) in ebook configuration
3. Update EbookConfig and ExtendedEbookConfig to include format selection based on ebook type
4. Add DPI validation constants: cover images 2550x2550px, content images 2175x2175px, content area 7.25" x 7.25"

### Phase 2: CSS and Template Updates

> Modify PDF rendering templates for square format

1. Update pdf_renderer.py _get_global_css() to include @page square-format rule (8.5" x 8.5")
2. Add KDP-compliant margins CSS with outer 0.5" and inner 0.75" spacing
3. Modify coloring_page.html template for 7.25" x 7.25" content area with object-fit: contain
4. Update cover_coloring.html template for square layout maintaining aspect ratios
5. Ensure all coloring templates use square page format class

### Phase 3: Image Quality and Resolution Control

> Implement 300+ DPI validation and processing

1. Add DPI validation functions in pdf_generator_adapter.py for quality control
2. Update OpenAI image generation with dual targets: 2550x2550+ pixels for covers, 2175x2175+ pixels for content
3. Modify cover image generation to ensure 2550x2550 minimum resolution for full 8.5" coverage
4. Update _optimize_image_for_pdf() to maintain DPI requirements and validate resolution by image type
5. Add error handling and logging for images below 300 DPI threshold with cover/content distinction
6. Implement resolution checking during image processing pipeline

### Phase 4: PDF Renderer Integration

> Connect square format with existing PDF generation system

1. Update PdfRenderer constructor to accept page format configuration
2. Modify generate_pdf_from_pages() to select CSS based on ebook type (coloring = square)
3. Update _wrap_with_layout() to apply appropriate page format styles
4. Ensure WeasyPrint uses correct page dimensions for square format
5. Test format selection logic in modular PDF generation

### Phase 5: Validation and Testing

> Ensure KDP compliance and quality assurance

1. Create unit tests for square format PDF generation with DPI validation
2. Add integration tests verifying final PDF dimensions and margins
3. Test image quality and DPI compliance in generated coloring PDFs
4. Validate KDP technical requirements (margins, resolution, format)
5. Add E2E tests for coloring ebook creation with square format

## Reviewed implementation

- [ ] Phase 1: Configuration and Constants
- [ ] Phase 2: CSS and Template Updates
- [ ] Phase 3: Image Quality and Resolution Control
- [ ] Phase 4: PDF Renderer Integration
- [ ] Phase 5: Validation and Testing

## Validation flow

1. Create a new coloring ebook through the web interface
2. Generate PDF and verify page dimensions are exactly 8.5" x 8.5"
3. Check margins: 0.5" outer, 0.75" inner using PDF measurement tools
4. Validate all images are ≥300 DPI in final PDF
5. Confirm content area is properly sized at 7.25" x 7.25"
6. Test print preview shows KDP-compliant format
7. Verify story ebooks remain A4 format (unchanged)

## Estimations

- High confidence (9/10)
- 6-8 hours implementation time