# Instruction: Orchestrator Interface - Real-time Production Monitoring and Control

## Feature

- **Summary**: Create comprehensive orchestrator interface with real-time pipeline visualization, production tracking, AI agent monitoring, memory insights, and configuration management. Provides full visibility and control over automated ebook production without modifying existing dashboard or ebook features.
- **Stack**: `Python 3.11+`, `FastAPI 0.100+`, `SQLAlchemy 2.0+`, `HTMX 1.9`, `Bootstrap 5.3`, `Jinja2 3.1+`, `PostgreSQL 15+`, `threading` (for singleton)

## Existing files

- @src/backoffice/features/orchestrator/market_analysis/presentation/routes/__init__.py
- @src/backoffice/features/ebook/shared/domain/services/book_memory_service.py
- @src/backoffice/features/ebook/shared/presentation/routes/memory_routes.py
- @src/backoffice/features/orchestrator/market_analysis/use_cases/analyze_market_use_case.py
- @src/backoffice/features/ebook/creation/domain/usecases/create_ebook.py
- @src/backoffice/features/shared/presentation/templates/dashboard.html
- @src/backoffice/features/shared/presentation/static/css/dashboard.css
- @src/backoffice/features/shared/presentation/static/js/dashboard.js
- @src/backoffice/main.py

### New files to create

- src/backoffice/features/orchestrator/pipeline/domain/entities/production.py
- src/backoffice/features/orchestrator/pipeline/domain/entities/orchestrator_config.py
- src/backoffice/features/orchestrator/pipeline/domain/entities/agent_status.py
- src/backoffice/features/orchestrator/pipeline/domain/services/production_tracker.py
- src/backoffice/features/orchestrator/pipeline/domain/services/pipeline_orchestrator.py
- src/backoffice/features/orchestrator/pipeline/infrastructure/models/orchestrator_config_model.py
- src/backoffice/features/orchestrator/pipeline/use_cases/start_production_use_case.py
- src/backoffice/features/orchestrator/pipeline/use_cases/get_pipeline_status_use_case.py
- src/backoffice/features/orchestrator/pipeline/use_cases/get_agents_status_use_case.py
- src/backoffice/features/orchestrator/pipeline/use_cases/update_config_use_case.py
- src/backoffice/features/orchestrator/pipeline/use_cases/get_memory_stats_use_case.py
- src/backoffice/features/orchestrator/pipeline/presentation/routes/__init__.py
- src/backoffice/features/orchestrator/pipeline/presentation/templates/orchestrator.html
- src/backoffice/features/orchestrator/pipeline/presentation/templates/partials/pipeline_view.html
- src/backoffice/features/orchestrator/pipeline/presentation/templates/partials/productions_table.html
- src/backoffice/features/orchestrator/pipeline/presentation/templates/partials/agents_grid.html
- src/backoffice/features/orchestrator/pipeline/presentation/templates/partials/memory_stats.html
- src/backoffice/features/orchestrator/pipeline/presentation/templates/partials/config_form.html
- src/backoffice/features/orchestrator/pipeline/presentation/templates/partials/logs_view.html
- src/backoffice/features/shared/presentation/static/js/orchestrator.js
- src/backoffice/migrations/versions/{timestamp}_add_orchestrator_config.py

## Implementation phases

### Phase 1: Backend Foundation

> Create domain entities and thread-safe tracking services

1. Create `Production` entity with fields: id, theme, current_stage (1-7), progress (current/total), status (active/paused/error/completed), started_at, logs, ebook_id
2. Create `AgentStatus` entity with fields: name, status (idle/active/error), progress, last_activity, metrics
3. Create `OrchestratorConfig` entity with fields: mode (auto/semi/manual), max_concurrent_productions, poll_interval, enabled_agents
4. Create `ProductionTracker` service as thread-safe Singleton using threading.Lock and __new__ pattern
5. Implement Singleton with _instance class variable, _lock (threading.Lock), and productions dict initialized once
6. Implement methods: create_production(), update_stage(), update_progress(), get_all_active(), get_by_id(), mark_completed(), add_log()
7. Add thread-safe access to productions dict using context manager with self._lock
8. Create `PipelineOrchestrator` service with 7 pipeline stages: analyze_market, ai_decision, generate_images, post_process, assemble_pdf, validate, publish
9. Implement orchestrate_production() method tracking stage changes via ProductionTracker
10. Create SQLAlchemy model `OrchestratorConfigModel` and Alembic migration for orchestrator_config table

### Phase 2: API Layer with Real Integration

> Build REST endpoints calling existing ebook creation use cases

1. Create `StartProductionUseCase` that receives optional theme parameter
2. If no theme provided, call AnalyzeMarketUseCase to get best opportunity from market analysis
3. Call BookMemoryService.analyze_niche() to validate theme is not saturated
4. Create Production entity in ProductionTracker with status "active" and stage 1
5. Import and call real CreateEbookUseCase from features/ebook/creation with GenerationRequest built from theme
6. Update Production entity with ebook_id after creation, update stages as ebook progresses
7. Handle errors by marking Production status as "error" and logging error message
8. Create `GetPipelineStatusUseCase` that queries ProductionTracker for active productions
9. Create `GetAgentsStatusUseCase` returning agent states derived from current production stages
10. Create FastAPI router at `/api/orchestrator` with endpoints: POST /production/start, GET /pipeline/status, GET /agents/status, GET /productions, GET /logs, GET /config, POST /config

### Phase 3: Frontend Structure

> Create main orchestrator page with navigation

1. Create `orchestrator.html` template inheriting dashboard layout structure (sidebar + main content)
2. Add sidebar navigation with 5 tabs: Pipeline, Productions, Agents, Memory, Config, Logs
3. Add page header with title "Orchestrator" and quick action buttons (Start Production, Pause All, Emergency Stop)
4. Create tab content areas with HTMX hx-get attributes for lazy loading
5. Add orchestrator route in main.py: GET /orchestrator serving orchestrator.html
6. Update dashboard.html sidebar to include link to /orchestrator page with icon
7. Create orchestrator.js for tab switching logic and HTMX event handlers
8. Add CSS classes in dashboard.css for orchestrator-specific styling (pipeline stages, agent cards, pulse animations)
9. Test navigation between dashboard and orchestrator pages
10. Verify Bootstrap styling consistency and responsive design

### Phase 4: Tab Implementation - Pipeline View

> Implement visual pipeline with 7 stages and real-time updates

1. Create `pipeline_view.html` partial with 7-stage horizontal progress bar using Bootstrap progress component
2. Add stage indicators: 1-Analyze Market, 2-AI Decision, 3-Generate Images (30 images), 4-Post-Process, 5-Assemble PDF, 6-Validate, 7-Publish
3. Implement stage status badges: pending (gray), active (blue with pulse animation), completed (green checkmark), error (red X)
4. Add progress percentage display under active stage (e.g., "15/30 images" for stage 3)
5. Include current production theme, ID, and started_at timestamp at top
6. Add "No active production" empty state with "Start Production" CTA button
7. Wire HTMX hx-get="/api/orchestrator/pipeline/status" with hx-trigger="every 5s"
8. Add loading skeleton using Bootstrap placeholders while fetching data
9. Implement stage transition animations with CSS keyframes for pulse effect
10. Test real-time updates by calling POST /production/start and observing stage progression

### Phase 5: Tab Implementation - Productions Table

> Show all active productions in table format

1. Create `productions_table.html` partial with Bootstrap table and striped rows
2. Add columns: ID, Theme, Current Stage (1-7 with stage name), Progress Bar, Status Badge, Started At, Actions
3. Implement status badges with colors: active (blue), paused (yellow), error (red), completed (green)
4. Add progress bar using Bootstrap progress component showing percentage (current_stage / 7 * 100)
5. Add "No active productions" empty state with message
6. Wire HTMX hx-get="/api/orchestrator/productions" with hx-trigger="every 5s"
7. Add pagination if more than 10 productions using Bootstrap pagination component (for future)
8. Implement filter buttons: All, Active, Paused, Error, Completed using HTMX hx-get with query params
9. Add action buttons with HTMX handlers: hx-post="/api/orchestrator/production/{id}/pause" and /stop
10. Test with multiple concurrent productions started manually

### Phase 6: Tab Implementation - Agents Grid

> Display 6 AI agent status cards with derived states

1. Create `agents_grid.html` partial with Bootstrap card grid using row with 3 columns (2 rows)
2. Create agent cards for: MarketScoutAI, DecisionEngineAI, ImageGenAI, PostProcessorAI, AssemblyAI, PublisherAI
3. Add agent card components: icon (Font Awesome), name, status badge (idle/active/error), progress bar (if active), last activity timestamp
4. Implement status badge colors: idle (secondary/gray), active (success/green with pulse), error (danger/red)
5. Add animated progress bar when agent is active (Bootstrap progress-bar-animated class)
6. Display metrics: tasks completed (count from ProductionTracker logs), avg duration (placeholder), success rate (placeholder)
7. Derive agent status from current production stage: MarketScoutAI active when stage 1, ImageGenAI active when stage 3, etc.
8. Wire HTMX hx-get="/api/orchestrator/agents/status" with hx-trigger="every 5s"
9. Add tooltip on hover showing agent capabilities using Bootstrap tooltips
10. Test agent state transitions during production (active agents should match current stage)

### Phase 7: Tab Implementation - Memory Stats with Real Data

> Aggregate and display memory insights from book_memory table

1. Create `memory_stats.html` partial with 4 stat cards in 2x2 grid using Bootstrap cards
2. Card 1 "Recent Productions": Query BookMemoryModel for last 5 entries ordered by created_at DESC, display theme and date
3. Card 2 "Saturation Levels": Query book_memory with 30-day filter grouped by theme, calculate recent_count, show top 3 themes with saturation bars
4. Card 3 "Top Performers": Query book_memory grouped by theme with COUNT, display top 5 most created themes with count badges
5. Card 4 "Patterns": Calculate real statistics from book_memory using Counter for theme frequencies, display most created theme and saturation count
6. Create `GetMemoryStatsUseCase` that uses BookMemoryService to fetch and aggregate data
7. Implement aggregation logic: themes_count = Counter([b.theme for b in recent]), saturation = len([t for t in themes_count if themes_count[t] > 3])
8. Wire HTMX hx-get="/api/orchestrator/memory/stats" with hx-trigger="load, every 10s"
9. Add date range filter dropdown (Last 7 days, 30 days, 90 days) using HTMX with hx-get params
10. Test with existing book_memory data and verify accurate aggregations

### Phase 8: Tab Implementation - Configuration

> Settings form for orchestrator behavior with database persistence

1. Create `config_form.html` partial with Bootstrap form using form-control classes
2. Add mode selection radio buttons: Auto (launch every hour), Semi (require approval), Manual (buttons only)
3. Add generation parameters: page_count (default 30), model selection dropdown (FLUX.1-dev/schnell), quality settings slider
4. Add toggle switches using Bootstrap form-check-switch: enable_market_analysis, enable_duplicate_check, enable_auto_publish
5. Add numeric inputs: max_concurrent_productions (1-5), poll_interval (3-10 seconds) with validation
6. Implement form validation with HTML5 required and min/max attributes
7. Wire form submission with HTMX hx-post="/api/orchestrator/config" hx-swap="none" and success handler
8. Add success/error toast notifications using Bootstrap toasts after save
9. Load current config on page load with hx-get="/api/orchestrator/config" hx-trigger="load" hx-target="#config-form"
10. Test configuration persistence by saving, reloading page, and verifying values

### Phase 9: Tab Implementation - Logs

> Real-time log viewer streaming from ProductionTracker

1. Create `logs_view.html` partial with scrollable container (max-height: 500px, overflow-y: auto)
2. Implement log entry format: `[HH:MM:SS] [LEVEL] message` with monospace font
3. Add log level colors using Bootstrap text utilities: success (text-success), info (text-info), warning (text-warning), error (text-danger)
4. Implement auto-scroll to bottom on new logs using JavaScript scrollIntoView
5. Add filter dropdown: All, Success, Info, Warning, Error using HTMX hx-get with filter param
6. Add "Clear Logs" button that clears DOM only (hx-swap="innerHTML" with empty response)
7. Wire HTMX hx-get="/api/orchestrator/logs" with hx-trigger="every 3s" fetching from ProductionTracker
8. Add "Pause auto-refresh" toggle button that stops/resumes HTMX polling
9. Implement search input for log text filtering (client-side using JavaScript)
10. Test with production logs streaming during ebook creation

### Phase 10: Integration & Polish

> Connect all components and verify end-to-end functionality

1. Wire StartProductionUseCase to call real CreateEbookUseCase from features/ebook/creation
2. Pass GenerationRequest with theme from market analysis, age_group, page_count from config
3. Update Production entity in ProductionTracker as ebook creation progresses through stages
4. Add error handling: catch exceptions from CreateEbookUseCase, mark Production status as "error", log error message
5. Test full pipeline: Start Production button → Market Analysis → Memory Check → Create Ebook → Track Progress → Mark Completed
6. Verify BookMemoryService integration: duplicate check blocks saturated themes, remember_ebook called after creation
7. Add global HTMX error handling with htmx:responseError event listeners showing Bootstrap alerts
8. Implement loading states using HTMX indicators (spinner-border classes) for all requests
9. Test concurrent production tracking: start 3 ebooks simultaneously, verify all tracked independently
10. Manual E2E test: Navigate to /orchestrator, click Start Production, verify Pipeline view updates every 5s, check Agents tab shows active agents, verify Memory stats updated after completion, test config persistence

## Reviewed implementation

- [ ] Phase 1: Backend Foundation
- [ ] Phase 2: API Layer with Real Integration
- [ ] Phase 3: Frontend Structure
- [ ] Phase 4: Tab Implementation - Pipeline View
- [ ] Phase 5: Tab Implementation - Productions Table
- [ ] Phase 6: Tab Implementation - Agents Grid
- [ ] Phase 7: Tab Implementation - Memory Stats with Real Data
- [ ] Phase 8: Tab Implementation - Configuration
- [ ] Phase 9: Tab Implementation - Logs
- [ ] Phase 10: Integration & Polish

## Validation flow

1. User navigates to dashboard at http://localhost:8001
2. User clicks "Orchestrator" link in sidebar (new link with robot icon)
3. User lands on /orchestrator page showing Pipeline tab by default
4. User sees "No active production" empty state with blue "Start Production" CTA button
5. User clicks "Start Production" button (triggers POST /api/orchestrator/production/start)
6. System calls GET /api/market/analyze to get best opportunity from MarketScoutBasic
7. System validates theme is not saturated using BookMemoryService.analyze_niche()
8. System creates Production entity in ProductionTracker (Singleton, thread-safe)
9. System calls real CreateEbookUseCase with GenerationRequest(theme, age_group, page_count)
10. Pipeline view updates to Stage 1 "Analyze Market" with blue pulse animation (HTMX poll every 5s)
11. User switches to Productions tab and sees active production in table with ID, theme, progress bar (1/7), status badge (active/blue)
12. Ebook creation progresses through stages 2-7, ProductionTracker updates current_stage and progress
13. User switches to Agents tab and sees ImageGenAI agent card with status "active" (green pulse) during Stage 3 (Generate Images)
14. Agent card shows progress "15/30 images" derived from Production entity progress
15. User switches to Memory tab and sees 4 cards with real data from book_memory table
16. Recent Productions card shows last 5 themes with dates, Top Performers shows most created themes with counts
17. User switches to Config tab, changes mode to "Semi", sets page_count to 25, clicks "Save Configuration"
18. System saves to orchestrator_config table, shows success toast notification
19. User switches to Logs tab and sees real-time timestamped logs: "[10:23:45] [INFO] Market analysis completed - theme: pirate"
20. Production completes all 7 stages, pipeline shows Stage 7 "Publish" with green checkmark, status changes to "completed" (green badge)
21. BookMemoryService.remember_ebook() called automatically, Memory stats updated on next poll
22. User clicks "Start Production" again, system prevents duplicate if same theme saturated
23. User can start another production with different theme, both tracked independently in Productions table
24. User can filter productions by status (All/Active/Completed), see accurate counts
25. User can view agent metrics updated based on completed tasks

## Estimations

- **Confidence**: 9/10
- **Time to implement**: 6-7 days (48-56 hours)

### Confidence Breakdown

✅ Reasons for high confidence:
- Clear requirements with detailed user stories and mockups provided
- Existing backend services (market_analysis, book_memory, create_ebook) already implemented and tested
- Thread-safe Singleton pattern for ProductionTracker prevents race conditions
- Real integration with CreateEbookUseCase ensures accurate production tracking
- Real data aggregation from book_memory table provides meaningful insights
- HTMX and Bootstrap already integrated in codebase, familiar tech stack
- Feature-based architecture is well-defined, new module follows established patterns
- No modifications required to existing dashboard or ebook features (isolated development)
- MVP scope is well-defined with clear v2 features excluded
- Polling approach is simpler than WebSocket, reduces complexity

❌ Reasons for low confidence / risks:
- In-memory production tracking (even with Singleton) loses state on server restart (acceptable for MVP but may confuse users)
- HTMX polling every 3-5 seconds on multiple tabs could impact server performance with many concurrent users (needs load testing)
- Agent status derived from production stage may not reflect actual execution state if CreateEbookUseCase fails mid-stage
- Pipeline orchestration must handle errors gracefully to avoid stuck productions (requires comprehensive try-catch)
- No authentication/authorization specified for orchestrator endpoints, assumes single-user or trusted environment
- Real-time updates tested manually, no automated E2E tests planned for MVP (may miss edge cases)
- Migration for orchestrator_config table may conflict if schema changes during development
- Thread-safety of ProductionTracker assumes CPython GIL, may need locks for PyPy or multi-process deployments

### Time Breakdown by Phase:
- Phase 1 (Backend Foundation + Singleton): 9 hours
- Phase 2 (API Layer + Real Integration): 7 hours
- Phase 3 (Frontend Structure): 4 hours
- Phase 4 (Pipeline View): 4 hours
- Phase 5 (Productions Table): 4 hours
- Phase 6 (Agents Grid): 4 hours
- Phase 7 (Memory Stats with Real Data): 5 hours
- Phase 8 (Configuration): 4 hours
- Phase 9 (Logs): 3 hours
- Phase 10 (Integration & Polish): 9 hours

**Total: 53 hours (6.5-7 days at 8 hours/day)**
