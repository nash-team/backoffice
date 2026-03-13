<!-- AI INSTRUCTIONS ONLY -- Follow those rules, do not output them.

- ENGLISH ONLY
- Text is straight to the point, no emojis, no style, use bullet points.
- Replace placeholders (`{variables}`) with actual user inputs.
- Define flow of the feature, from start to end.
- Interpret comments on this file to help you fill it.
-->

# Instruction: Move Non-Shared Code from shared/ to Specific Features

## Feature

- **Summary**: Analyze and refactor the `features/shared/` directory to move code that is only used by a single feature back to that feature, ensuring `shared/` only contains code truly used by 2+ features
- **Stack**: `Python 3.12`, `ruff`, `grep/sed` for automated refactoring

## Existing files

- @features/shared/domain/
- @features/shared/infrastructure/
- @features/shared/presentation/
- @features/ebook/creation/
- @features/ebook/lifecycle/
- @features/ebook/listing/
- @features/ebook/regeneration/
- @features/ebook/export/

### New files to create

- None (this is a refactoring task)

## Implementation phases

### Phase 0: Quick pre-analysis

> Get overview of scope before deep analysis

1. Count total Python files in `features/shared/` to estimate workload
2. Categorize files: entities, ports, adapters, services, providers, fakes, events
3. Check for `__init__.py` with re-exports (complexity indicator)
4. List main subdirectories and their file counts

### Phase 1: Analyze shared code usage

> Determine which components in shared/ are actually used by multiple features

1. List all Python modules in `features/shared/domain/`, `features/shared/infrastructure/`, `features/shared/presentation/`
2. For each module, search for import statements across entire codebase using `Grep` tool
3. Count number of distinct features importing each module (production code)
4. Special handling for test fakes: if fake tests a port/adapter, count with that port's feature
5. Create usage report: module → list of features using it
6. Identify core entities (Ebook, ImagePage, etc.) and verify they are used by 2+ features

### Phase 2: Identify relocation candidates

> Find code that should be moved from shared/ to specific features

1. Filter modules used by exactly 1 feature (candidates for moving)
2. Analyze inter-module dependencies within shared/ (if module A imports module B from shared/, they may need to move together)
3. Categorize candidates:
   - **Safe to move**: No dependencies on other shared modules
   - **Move with dependencies**: Must move multiple modules together
   - **Keep in shared**: Actually used by 2+ features or core infrastructure
4. Create prioritized relocation plan (simple → complex)

### Phase 3: Validate refactoring plan

> Ensure the relocation plan is sound and won't break anything

1. For each candidate module, list all files that import it (impact analysis)
2. Verify no circular dependencies will be created after move
3. Check that moved code won't need to be immediately re-shared (YAGNI validation)
4. Simulate moves with dry-run (generate list of git mv commands without executing)
5. Generate complete list of import changes needed (old path → new path)
6. Present plan summary to user for approval before execution

### Phase 4: Execute refactoring

> Move code from shared/ to features and update imports

1. Start with simplest candidates (no dependencies)
2. For each module to move:
   - Move file(s) from `features/shared/` to `features/<feature_name>/`
   - Update import statements across codebase using `LC_ALL=C find ... sed` pattern
   - Verify syntax after each batch of changes
3. Remove empty directories in `shared/` if created
4. Update any documentation referencing old paths

### Phase 5: Validation and quality checks

> Ensure refactoring didn't break anything

1. Run unit tests: `make test`
2. Run smoke test: `make test-smoke`
3. Run type checking: `make typecheck`
4. Run linting: `make lint`
5. Verify import correctness: `PYTHONPATH=./src lint-imports`
6. If any failures, fix and re-run checks

## Reviewed implementation

<!-- That section is filled by a review agent that ensures feature has been properly implemented -->

- [ ] Phase 0: Pre-analysis completed
- [ ] Phase 1: Usage analysis completed
- [ ] Phase 2: Candidates identified
- [ ] Phase 3: Plan validated and approved by user
- [ ] Phase 4: Code moved and imports updated
- [ ] Phase 5: All tests passing

## Validation flow

<!-- What would a REAL user do to 100% validate the feature? -->

1. Run `make test` - all 146 unit tests should pass
2. Run `make test-smoke` - E2E smoke test should pass
3. Run `make typecheck` - no type errors
4. Run `make lint` - no linting errors
5. Verify `features/shared/` only contains code used by 2+ features
6. Check that moved code is in the correct feature directory
7. Confirm all imports are correct and no broken references

## Estimations

- **Confidence**: 9/10
  - ✅ Clear architecture principles to follow
  - ✅ Strong test coverage (146 tests) to detect regressions
  - ✅ Automated refactoring tools (grep/sed/ruff)
  - ✅ Safe refactoring (just moving files, no logic changes)
  - ✅ Phase 0 pre-analysis reduces unknowns
  - ✅ Dry-run validation before execution (Phase 3)
  - ❌ Scope unknown until Phase 0 completes (may be 0 or 50+ files)
  - ❌ Test fakes add complexity (shared by multiple features)
  - ❌ Potential inter-module dependencies in shared/

- **Time to implement**:
  - Phase 0 (pre-analysis): 5-10 minutes
  - Phase 1 (usage analysis): 15-30 minutes (depends on file count)
  - Phase 2 (identify candidates): 10-15 minutes
  - Phase 3 (validate plan): 10-15 minutes
  - Phase 4 (execute refactoring): 20-60 minutes (depends on number of moves)
  - Phase 5 (validation): 5-10 minutes
  - **Total estimate**: 1-2 hours (if moderate amount of code to move)
