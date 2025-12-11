# Instruction: Google OAuth Authentication

## Feature

- **Summary**: Add Google OAuth login with email whitelist, 30-day sessions, and route protection. Only 3 authorized emails can access the app.
- **Stack**: `FastAPI 0`, `Authlib 1`, `itsdangerous 2`, `Jinja2 3`

## Existing files

- @src/backoffice/main.py
- @src/backoffice/features/shared/presentation/templates/layouts/base.html
- @src/backoffice/features/shared/presentation/templates/login.html
- @src/backoffice/features/shared/presentation/static/css/login.css
- @src/backoffice/features/shared/presentation/routes/templates.py
- @pyproject.toml

### New files to create

- config/auth/allowed_emails.yaml
- src/backoffice/features/auth/presentation/routes/__init__.py
- src/backoffice/features/auth/infrastructure/middleware.py
- src/backoffice/features/auth/infrastructure/session.py

## Implementation phases

### Phase 1: Configuration & Dependencies

> Add OAuth libraries and create allowed emails config file

1. Add `authlib>=1.3.0` and `itsdangerous>=2.1.0` to pyproject.toml
2. Add env vars to `.env.example`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET_KEY`
3. Create `config/auth/allowed_emails.yaml` with the 3 authorized emails
4. Run `pip install -e .` to install new dependencies

### Phase 2: Auth Feature Backend

> Create auth feature with OAuth routes and session management

1. Create `features/auth/` folder structure (presentation/routes/, infrastructure/)
2. Create session helper (`infrastructure/session.py`) using itsdangerous for signed cookies (30 days expiry)
3. Create auth routes (`presentation/routes/__init__.py`):
   - `GET /login` - render login page
   - `GET /auth/google` - redirect to Google OAuth
   - `GET /auth/google/callback` - handle OAuth callback, check email whitelist, create session
   - `POST /logout` - destroy session, redirect to /login
4. Load allowed emails from YAML config at startup

### Phase 3: Frontend Interface

> Simple login page + logout button in header

1. Update `login.html` - simple centered "Se connecter avec Google" button linking to `/auth/google`
2. Update `base.html` - add logout button in sidebar (POST to `/logout`)
3. Style logout button with existing CSS classes

### Phase 4: Route Protection Middleware

> Middleware redirecting unauthenticated users to /login

1. Create auth middleware (`infrastructure/middleware.py`) that:
   - Excludes `/login`, `/auth/*`, `/static/*`, `/healthz` from protection
   - Checks for valid session cookie
   - Redirects to `/login` with error message if session expired/invalid
2. Register middleware in `main.py` (before CORS)
3. Register auth router in `main.py`

## Reviewed implementation

- [x] Phase 1: Configuration & Dependencies
- [x] Phase 2: Auth Feature Backend
- [x] Phase 3: Frontend Interface
- [x] Phase 4: Route Protection Middleware

## Validation flow

1. Start app with `make run`
2. Navigate to `http://localhost:8001` → should redirect to `/login`
3. Click "Se connecter avec Google" → redirected to Google
4. Login with authorized email (franck.marchand@gmail.com) → redirected to dashboard
5. Refresh page → still logged in (session persists)
6. Click logout button → redirected to `/login`
7. Try login with unauthorized email → error message "Accès non autorisé"
8. Wait 30 days (or manually expire cookie) → redirected to `/login` with expiration message

## Estimations

- **Confidence**: 9/10
  - ✅ Standard OAuth flow with well-documented libraries
  - ✅ Simple whitelist logic (no complex roles)
  - ✅ Existing login.html template to update
  - ✅ Clear feature-based architecture to follow
  - ❌ Minor risk: Google OAuth console setup required (external dependency)
- **Time to implement**: ~2-3 hours
