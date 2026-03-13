# Testing

## Tools

- **Vitest 3**: Test runner (Vite-native)
- **jsdom**: DOM simulation environment
- Config: @frontend/vitest.config.ts

## Strategy

- **Chicago-style**: Fakes over mocks (mirrors backend approach)
- **Co-located tests**: `features/ebooks/tests/unit/`
- **Global fakes**: `src/tests/fakes/`

## Execution

- `npm run test` — Run once
- `npm run test:watch` — Watch mode
- `make frontend-test` — From project root

## Available Fakes

Located in `@frontend/src/tests/fakes/`:

| Fake | Implements | Tracks |
|------|-----------|--------|
| `FakeEbookGateway` | `EbookGateway` | `callCounts` per method, in-memory ebook store |
| `FakeExportGateway` | `ExportGateway` | Call counts |
| `FakeRegenerationGateway` | `RegenerationGateway` | Call counts |

## Fake Pattern

```typescript
const gateway = new FakeEbookGateway()
const store = createAppStore({ ebookGateway: gateway, ... })

await store.dispatch(listEbooks({ page: 1 }))

expect(gateway.callCounts.list).toBe(1)
expect(store.getState().ebooks.items).toHaveLength(...)
```

- Fakes implement full gateway interface
- In-memory storage for stateful operations
- No mocking library needed

## Test Coverage

- Use case thunks (list, create, approve, reject, stats, formConfig)
- Redux selectors
- No component/E2E tests yet (UI evolves rapidly)

## Naming

- Files: `*.test.ts` (e.g., `ebook-usecases.test.ts`)
- Functions: `describe('usecase')` + `it('should ...')`
