# Instruction: Add Image Edit Button for Targeted Corrections

## Feature

- **Summary**: Add "Edit" button to page edit modal allowing targeted image corrections via edit prompt without full regeneration. Supports Comfy UI (Qwen Image Edit 2509) and Gemini providers. User enters correction prompt, system sends existing image + prompt to edit provider, preview updates in modal.
- **Stack**: `FastAPI 0.104+`, `Jinja2 3.1+`, `Bootstrap 5.3`, `SQLAlchemy 2.0+`, `Python 3.11+`, `HTMX 1.9+`, `ComfyUI`, `Gemini API`, `httpx`

## Existing files

- `src/backoffice/features/ebook/regeneration/presentation/templates/partials/edit_page_modal.html` (modal with Regenerate button)
- `src/backoffice/features/ebook/regeneration/presentation/routes/__init__.py` (regeneration API routes)
- `src/backoffice/features/ebook/shared/infrastructure/providers/provider_factory.py` (provider factory)
- `src/backoffice/features/ebook/shared/infrastructure/providers/images/gemini/gemini_image_provider.py` (Gemini provider)
- `src/backoffice/features/ebook/shared/infrastructure/providers/images/comfy/comfy_provider.py` (Comfy provider)
- `src/backoffice/features/ebook/shared/domain/ports/content_page_generation_port.py` (generation port interface)
- `config/generation/models.yaml` (provider configuration)

### New files to create

- `src/backoffice/features/ebook/shared/domain/ports/image_edit_port.py` (port for image editing)
- `src/backoffice/features/ebook/regeneration/domain/usecases/edit_page_image.py` (edit use case)
- `src/backoffice/features/ebook/regeneration/tests/unit/domain/usecases/test_edit_page_image.py` (unit tests for edit)
- `src/backoffice/features/shared/tests/unit/fakes/fake_image_edit_port.py` (fake for testing)

## Implementation phases

### Phase 1: Infrastructure - Image Edit Port and Adapters

> Create image editing interface and implement for Comfy UI and Gemini providers

1. Create `ImageEditPort` interface in `shared/domain/ports/image_edit_port.py`
   - Abstract method `edit_image(image: bytes, edit_prompt: str, spec: ImageSpec) -> bytes`
   - Abstract method `is_available() -> bool`
   - Add docstrings explaining image editing vs generation
2. Add `edit_image()` method to `GeminiImageProvider` in `gemini_image_provider.py`
   - Send image as base64 in multipart request with edit prompt
   - Use Gemini API format: `{"contents": [{"parts": [{"inline_data": {"mime_type": "image/png", "data": base64}}, {"text": edit_prompt}]}]}`
   - Parse response and extract edited image
   - Handle errors with DomainError (ErrorCode.GENERATION_FAILED)
3. Add `edit_image()` method to `ComfyProvider` in `comfy_provider.py`
   - Load Qwen Image Edit 2509 workflow JSON if model contains "edit"
   - Send image + edit_prompt to workflow
   - Wait for completion via WebSocket
   - Extract edited image from output
4. Update `ProviderFactory` in `provider_factory.py`
   - Add `create_image_edit_provider()` method
   - Reuse same provider as `coloring_page` (reads from models.yaml)
   - Return cached provider instance supporting ImageEditPort
5. Create `FakeImageEditPort` in `shared/tests/unit/fakes/fake_image_edit_port.py`
   - Mode: "succeed" (returns modified image), "fail" (raises error)
   - Track call count and last edit_prompt for assertions

### Phase 2: Backend - Edit Page Endpoint

> Create API endpoint for editing page with correction prompt

1. Create `EditPageImageUseCase` in `regeneration/domain/usecases/edit_page_image.py`
   - Validate ebook exists and is DRAFT status
   - Validate page_index is valid content page
   - Load current page image from `structure_json.pages_meta[page_index]`
   - Call `ImageEditPort.edit_image(image, edit_prompt, spec)`
   - Return edited image as base64 (no DB save, preview only)
   - Handle provider unavailable error
2. Add POST endpoint `/api/ebooks/{ebook_id}/pages/{page_index}/edit` in `regeneration/presentation/routes/__init__.py`
   - Inject dependencies (ebook_repo, image_edit_provider)
   - Parse JSON body: `{"edit_prompt": "..."}`
   - Call `EditPageImageUseCase.execute()`
   - Return JSON: `{"success": true, "image_base64": "...", "page_index": N}`
   - Handle errors (404 if not found, 400 if invalid status, 500 if edit fails)
3. Write unit tests in `regeneration/tests/unit/domain/usecases/test_edit_page_image.py`
   - Use `FakeEbookRepository` and `FakeImageEditPort`
   - Test: edit generates new image without DB save
   - Test: fails if ebook not DRAFT
   - Test: fails if invalid page_index
   - Test: fails if provider unavailable
   - Test: uses existing image + edit_prompt

### Phase 3: Frontend - Edit Button and Textarea in Modal

> Add Edit button and textarea to existing modal UI

1. Update modal template `regeneration/presentation/templates/partials/edit_page_modal.html`
   - Add textarea above buttons section with id `editPromptTextarea`
   - Placeholder: "Ex: remplace les 5 doigts des pattes arrière du dinosaure par 3 doigts"
   - Add "Edit" button next to "Regenerate" button (warning color, id `editBtn`)
   - Wire onclick to new `editPageImage()` JavaScript function
   - Add toggle logic to show/hide textarea when Edit mode active
2. Add `editPageImage()` JavaScript function in modal script section
   - Get edit_prompt from textarea
   - Validate edit_prompt is not empty (show error toast if empty)
   - Show loading spinner
   - POST to `/api/ebooks/${currentEbookId}/pages/${currentPageIndex}/edit` with `{"edit_prompt": "..."}`
   - On success: update `currentImageBase64` and preview image src
   - On error: display error toast, keep original image
   - Hide loading spinner
3. Update modal open logic in `openEditPageModal()`
   - Clear textarea on modal open
   - Reset Edit button state
4. Add visual distinction between Regenerate and Edit modes
   - "Regenerate" button: warning color (yellow), icon: sync-alt
   - "Edit" button: info color (blue), icon: magic

## Reviewed implementation

- [ ] Phase 1: Infrastructure - Image Edit Port and Adapters
- [ ] Phase 2: Backend - Edit Page Endpoint
- [ ] Phase 3: Frontend - Edit Button and Textarea in Modal

## Validation flow

1. Navigate to ebook detail page for a DRAFT ebook
2. Click "Edit" button on a content page (e.g., Page 1)
3. Modal opens showing current page image with Regenerate and Edit buttons
4. Enter edit prompt in textarea: "remplace les 5 doigts par 3 doigts"
5. Click "Edit" button
6. Spinner shows during processing
7. Image updates in modal with edited version (showing 3 toes instead of 5)
8. Try another edit: "enlève les couleurs"
9. Image updates again to black and white
10. Click "Apply" to save changes
11. Modal closes, PDF updates with edited page
12. Test error case: empty edit prompt shows error toast
13. Test with Comfy UI provider (Qwen workflow)
14. Test with Gemini provider (multipart request)

## Estimations

- **Confidence**: 8/10
  - ✅ Architecture is clear (port-adapter pattern established)
  - ✅ Modal infrastructure already exists (Regenerate button)
  - ✅ Provider factory pattern already implemented
  - ✅ Both Gemini and Comfy providers already functional
  - ✅ Test infrastructure ready (fakes, Chicago-style testing)
  - ❌ Risk: Qwen Image Edit 2509 workflow JSON might need creation/configuration
  - ❌ Risk: Gemini edit API format might differ from generation (needs testing)
  - ❌ Risk: Base64 image size in JSON payload (should be fine for 300 DPI pages)
- **Time to implement**: 5-7 hours
  - Phase 1 (Infrastructure): 2.5 hours (port + 2 adapters + factory + fake)
  - Phase 2 (Backend): 1.5 hours (use case + endpoint + tests)
  - Phase 3 (Frontend): 1.5 hours (textarea + button + JS wiring)
  - Testing & refinement: 1.5 hours (both providers, error cases)
