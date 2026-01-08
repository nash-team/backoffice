# Instruction: Flux 2 Prompt Diversity and Optimization

## Feature

- **Summary**: Adapt prompts and ComfyProvider for Flux 2 best practices (natural language, no negative prompts, Subject+Action+Style+Context structure) and enrich theme diversity while maintaining semantic coherence via species_profiles.
- **Stack**: `Python 3.12`, `ComfyUI`, `Flux 2 Dev`, `YAML`

## Existing files

- @config/branding/themes/christmas-creepy-cute.yml
- @src/backoffice/features/ebook/shared/infrastructure/providers/images/comfy/comfy_provider.py

### New file to create

- None

## Implementation phases

### Phase 1: ComfyProvider - Flux 2 Adaptation

> Add Flux 2 detection and prompt transformation in provider

1. Add `_is_flux2_workflow()` method: detect via model name containing "flux-2" or node 63 presence
2. Add `_transform_prompt_for_flux2(prompt: str) -> str` method:
   - Reorder to follow **Subject + Action + Style + Context** structure (priority at beginning)
   - Keep quality descriptors but use concrete references (e.g., "children's book illustration style")
   - Target 30-80 words (medium length, no hard cap)
   - Use natural language sentences, avoid keyword stacking
3. In `generate_page()`: if Flux 2, call transform before injecting into node 63
4. In `generate_cover()`: if Flux 2, call transform before injecting into node 6
5. Add `flux2_guidance` param support from workflow_params (default 4.5, matching doc example for [flex])

### Phase 2: Theme YAML - Reformulate for Flux 2

> Convert quality_settings to positive natural language (no negative phrasing)

1. Rewrite `_shared_quality_settings` anchor:
   - Replace "NO colors, NO gray" → "sharp clean white background, bold black line art"
   - Replace "NO FRAME, NO BORDER" → "illustration extends to edges naturally"
   - Keep useful info like "printable 300 DPI", "bold clean outlines"
2. Rewrite `_quality_children` prefix/suffix:
   - Replace "NO FRAME, NO BORDER, NO VIGNETTE" → "full-bleed illustration, edges blend naturally"
   - Replace "No cross-hatching, no gradients" → "solid black lines only, uniform weight"
   - Keep concrete style refs: "children's coloring book illustration"
3. Rewrite `_quality_adults` prefix/suffix similarly with positive phrasing
4. Update `comfy:` section in `coloring_page_templates`:
   - Remove `workflow_params["47"]` (negative prompt unused by Flux 2)
   - Add `flux2_guidance: 4.5`
   - Keep `clip_g_suffix` with concrete style references

### Phase 3: Theme YAML - Enrich Diversity

> Add more characters, actions, environments while keeping species_profiles coherence

1. Add 5-8 new CHARACTERs:
   - "cute mummy elf with bandages"
   - "friendly witch with pointy hat"
   - "adorable scarecrow snowman"
   - "sweet frankenstein helper"
   - "tiny werewolf in Christmas sweater"
2. Add 3-5 new ACTIONs:
   - "reading a spooky Christmas story"
   - "ice skating on a frozen pond"
   - "building a haunted snowman"
3. Add 3-5 new ENVs:
   - "simple frozen pond with bare trees"
   - "simple enchanted forest path with lanterns"
   - "simple old clock tower with snow"
4. Add 2-3 new SECONDARY_ELEMENTS variations
5. Create `species_profiles` entries for new characters with coherent action/environment mappings

## Reviewed implementation

- [ ] Phase 1: ComfyProvider - Flux 2 Adaptation
- [ ] Phase 2: Theme YAML - Reformulate for Flux 2
- [ ] Phase 3: Theme YAML - Enrich Diversity

## Validation flow

1. Run existing unit tests: `make test`
2. Start ComfyUI with Flux 2 workflow
3. Generate 5 coloring pages with `christmas-creepy-cute` theme
4. Verify images: pure B&W line art, no gray, no text artifacts
5. Check diversity: different characters, actions, environments across generations
6. Verify coherence: no bizarre combinations (character-action-environment match)

## Estimations

- **Confidence**: 9/10
  - ✅ Clear Flux 2 documentation available (Subject+Action+Style+Context order)
  - ✅ Existing code structure supports changes
  - ✅ species_profiles mechanism already handles coherence
  - ✅ Guidance configurable per theme (no hardcoded default)
  - ❌ Risk: Flux 2 prompt behavior may need iterative tuning
- **Complexity**: Medium (mostly YAML editing + small provider changes)

## References

- [Flux 2 Prompting Guide - Black Forest Labs](https://docs.bfl.ml/guides/prompting_guide_flux2)
- [Flux 2 Guide - Apatero](https://apatero.com/blog/flux-2-official-prompting-guide-black-forest-labs-2025)
