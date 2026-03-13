# Code Review for React SPA Migration (`feature/react-migration`)

Migration du frontend HTMX/Jinja2 vers React 19 + Redux Toolkit + React Router 7 + Tailwind CSS 4. Ajout du fake provider avec progression WebSocket.

- Statuts: **Needs fixes**
- Confidence: **High** (tous les fichiers lus en detail)

## Main expected Changes

- [x] Frontend React SPA (nouveau dossier `frontend/`)
- [x] API JSON routes separees des routes HTMX (`/api/` vs `/htmx/`)
- [x] Fake image provider avec emission d'evenements de progression
- [x] `ebook_id`/`page_index` dans `ImageSpec` pour toutes les use cases
- [x] SPA catch-all + fallback Jinja2

## Scoring

### Potentially Unnecessary Elements

- [🔴] **Dead code**: `StatsCards.tsx`, `StatusFilter.tsx`, `StatusBadge.tsx`, `ConfirmDialog.tsx` — importent des exports/types inexistants (`selectStats`, `selectStatusFilter`, `EbookStatus`). Non utilises mais casseraient le build si importes.
- [🟡] **Dead code**: `HttpExportGateway` + `FakeExportGateway` — jamais utilises, `EbookDetailPage.tsx:56` fait un `fetch()` direct au lieu de passer par le gateway.
- [🟡] **Unused var**: `main.py:111` `loop_condition = True` — jamais mis a `False`, le while-loop tourne indefiniment.
- [🟡] **Commented code**: `main.py:132-137` — code commente dans le WebSocket handler.

---

### Standards Compliance

- [🟢] Naming conventions followed (composants PascalCase, hooks use*, thunks camelCase)
- [🟢] Feature-based architecture respected cote frontend
- [🟡] **Type circumvention**: `CreateEbookModal.tsx:51` — `title: '' as unknown as string` contourne le type system. Si le backend genere le titre, rendre `title` optionnel dans le type.
- [🟡] **Type mismatch**: `CreateEbookModal.tsx:38-41,110-112` — `FormConfig.themes` type `string[]` mais le code gere `string | { id: string; label?: string }` avec des assertions. Corriger le type `FormConfig`.
- [🟡] **Type assertions**: `ebook-usecases.ts:8`, `regeneration-usecases.ts` — `extra as Gateways` partout. Utiliser `createAsyncThunk.withTypes<>()` pour typer proprement.

---

### Architecture

- [🔴] **Auth bypass**: `middleware.py:25-26` — `/api/` et `/htmx/` ajoutes dans `PUBLIC_PATHS`. **Toutes les routes API sont accessibles sans authentification.** C'est acceptable en dev mais dangereux si oublie en prod.
- [🔴] **Port/adapter violation**: `EbookDetailPage.tsx:56` — `handleExport()` fait un `fetch()` direct au lieu d'utiliser le `ExportGateway`. L'adapter HTTP est du code mort.
- [🟡] **Port/adapter violation**: `PageGrid.tsx:82-87` (`PageThumbnail`) — `fetch()` direct pour charger les images au lieu du gateway.
- [🟡] **Port/adapter violation**: `KdpCoverPreviewModal.tsx:22` — `fetch()` direct au lieu du `ExportGateway`.
- [🟡] **SPA catch-all trop large**: `main.py:214-219` — `/{full_path:path}` matche tout, y compris les URLs d'API mal formees qui retourneront `index.html` au lieu d'un 404 JSON. Ajouter un guard: `if full_path.startswith("api/") or full_path.startswith("htmx/"): raise HTTPException(404)`.
- [🟡] **Tests fakes location**: `frontend/src/tests/fakes/` — devrait etre `frontend/src/features/ebooks/tests/fakes/` pour respecter la co-localisation.
- [🟡] **Toast via CustomEvent**: `Toast.tsx:39-43` — `window.dispatchEvent(new CustomEvent(...))` est un canal global mutable qui contourne React/Redux. Non testable sans DOM mocking.

---

### Code Health

- [🟢] Functions and files sizes OK
- [🟢] Cyclomatic complexity acceptable
- [🟡] **progress.status type**: `regeneration-slice.ts:8` — `status: string` mais c'est un nombre 0-100. `parseInt(progress.status)` dans les composants est fragile. Typer en `number`.
- [🟡] **Dynamic thunk loop**: `regeneration-slice.ts:147-158` — boucle `for...of` sur les thunks dans `extraReducers`. Clever mais rend difficile l'ajout de comportement specifique par thunk.

---

### Security

- [🔴] **Auth bypass**: `middleware.py:25-26` — `/api/` dans `PUBLIC_PATHS` rend TOUTES les API publiques. Ajouter l'auth cote API (ex: session cookie check dans les routes API) ou retirer `/api/` de `PUBLIC_PATHS`.
- [🟡] **SPA path traversal**: `main.py:219` — `FileResponse(FRONTEND_DIST / "index.html")` est safe (path fixe), mais le catch-all `{full_path:path}` pourrait masquer des erreurs 404 sur les endpoints API.
- [🟢] SQL injection risks — pas d'injection possible (ORM SQLAlchemy)
- [🟢] XSS vulnerabilities — React echappe par defaut, pas de `dangerouslySetInnerHTML`
- [🟢] CORS configuration OK (dev/staging/prod)
- [🟢] Environment variables secured

---

### Error management

- [🟡] **Silent catch**: `useRegenWebSocket.ts:46` — `ws.onerror = () => {}` avale les erreurs WebSocket silencieusement. Au moins un `console.warn`.
- [🟡] **Silent catch**: `PageGrid.tsx:86` — `.catch(() => {})` avale les erreurs fetch. L'utilisateur ne voit rien si le chargement echoue.
- [🟢] Error handling dans les use cases backend (DomainError, HTTPException)
- [🟢] Error toasts dans les composants React pour les actions utilisateur

---

### Performance

- [🟡] **Pagination non-tronquee**: `PaginationControls.tsx:30` — `Array.from({ length: totalPages })` rend tous les boutons. Avec 100+ pages, le DOM explose.
- [🟡] **ImageSpec recree a chaque iteration**: `add_new_pages.py:134-142` — l'`ImageSpec` est recree dans la boucle. Seul `page_index` change, le reste est constant. Mineur mais inutile.
- [🟢] WebSocket cleanup correct (fermeture a l'unmount)
- [🟢] `useCallback` utilise pour les handlers de selection

---

### Frontend specific

#### State Management

- [🟢] Loading states implemented (pageData.loading, preview.loading, bulkAction.loading)
- [🟢] Empty states designed ("Ebook not found", "No ebooks yet")
- [🟢] Error states handled (toasts)
- [🟢] Success feedback provided (toasts)
- [🟡] **Transition states**: passage spinner → progress bar corrige, mais `progress.status` reste `string` au lieu de `number`

#### UI/UX

- [🟢] Consistent design patterns (Tailwind utility classes)
- [🟡] **ExportDropdown**: `EbookDetailPage.tsx:149` — ne se ferme pas au clic exterieur
- [🟡] **URL.revokeObjectURL timing**: `useFileDownload.ts` — revoke immediat, certains navigateurs n'ont pas encore demarre le download. Ajouter `setTimeout(..., 100)`.
- [🟢] Responsive design (grid responsive, modal responsive)
- [🟢] Semantic HTML (dialog, form, button)

---

### Backend specific

#### FakeImageProvider (`fake_image_provider.py`)

- [🟢] Progress events emis correctement (0% → 20% → ... → 100%/finished)
- [🟢] Guard `if not spec.ebook_id or spec.page_index is None` evite les erreurs
- [🟡] **Couplage cross-feature**: `shared/infrastructure/providers/images/fake/` importe depuis `regeneration/domain/events/`. Le provider "shared" depend d'un event "regeneration". Acceptable car c'est un fake de test, mais a noter.
- [🟢] Delai simule (0.3s × 5 = 1.5s) realiste pour le test UI

#### WebSocket Handler (`main.py:109-140`)

- [🟡] **Subscribe before connect**: L'EventBus souscrit le handler (l.125) AVANT `manager.connect()` (l.128). Si un event arrive entre les deux, `broadcast()` essaiera d'envoyer sur un WebSocket non-accepte.
- [🟡] **`print()` au lieu de `logger`**: `main.py:129,140` — utiliser `logger.info()` pour la coherence.
- [🟡] **ConnectionManager.disconnect()**: `main.py:184` — `self.active_connections.remove(websocket)` leve `ValueError` si le websocket n'est pas dans la liste. Ajouter un guard.

#### Logging

- [🟢] Logging present dans tous les use cases backend
- [🟢] Logging present dans le FakeImageProvider

---

## Final Review

- **Score**: 6.5/10
- **Feedback**: La migration React est fonctionnelle avec une bonne architecture feature-based. Les problemes majeurs sont: (1) l'auth bypass sur `/api/` qui rend toutes les routes publiques, (2) les composants morts qui casseraient le build, et (3) le non-respect du pattern port/adapter cote export/thumbnails. Le backend (fake provider, ImageSpec, use cases) est propre.
- **Follow-up Actions**:
  1. **P0 Security**: Retirer `/api/` de `PUBLIC_PATHS` ou implementer l'auth API
  2. **P0 Dead code**: Supprimer `StatsCards.tsx`, `StatusFilter.tsx`, `StatusBadge.tsx`, `ConfirmDialog.tsx`
  3. **P1 Architecture**: Migrer `handleExport`, `PageThumbnail` fetch, et `KdpCoverPreviewModal` fetch vers les gateways
  4. **P1 Type safety**: Corriger `FormConfig` type, `progress.status: number`, supprimer `as unknown as string`
  5. **P2 UX**: Fermeture du dropdown au clic exterieur, troncation de la pagination
  6. **P2 Backend**: Inverser subscribe/connect dans le WS handler, remplacer `print` par `logger`
- **Additional Notes**: La strategie de migration (HTMX sous `/htmx/`, API sous `/api/`, SPA catch-all) est pragmatique et permet la cohabitation des deux frontends.
