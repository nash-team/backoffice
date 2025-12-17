"""Authentication routes for Google OAuth."""

import logging
import os
from pathlib import Path

import yaml
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backoffice.features.auth.infrastructure.session import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_DAYS,
    create_session_token,
)
from backoffice.features.shared.presentation.routes.templates import templates

load_dotenv()

logger = logging.getLogger(__name__)
DEBUG = os.getenv("DEBUG", "").lower() == "true"

router = APIRouter(tags=["auth"])

# Initialize OAuth client
is_testing = os.getenv("TESTING", "").lower() == "true"
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

if not google_client_id or not google_client_secret:
    if is_testing:
        google_client_id = google_client_id or "test-client-id"
        google_client_secret = google_client_secret or "test-client-secret"
    else:
        raise RuntimeError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment "
            "(.env) and ensure the redirect URI http://localhost:8001/auth/google/callback is authorized in Google Cloud."
        )

oauth = OAuth()
oauth.register(
    name="google",
    client_id=google_client_id,
    client_secret=google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def load_allowed_emails() -> list[str]:
    """Load allowed emails from config file."""
    config_path = Path(__file__).resolve().parents[6] / "config" / "auth" / "allowed_emails.yaml"
    if not config_path.exists():
        return []
    with open(config_path) as f:
        config = yaml.safe_load(f)
    emails: list[str] = config.get("allowed_emails", [])
    return emails


@router.get("/login")
async def login_page(request: Request, error: str | None = None):
    """Render the login page."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error},
    )


@router.get("/auth/google")
async def google_login(request: Request):
    """Redirect to Google OAuth."""
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error(f"OAuth token error: {e}")
        return RedirectResponse(url="/login?error=auth_failed", status_code=302)

    user_info = token.get("userinfo")
    if DEBUG:
        logger.debug(f"OAuth userinfo: {user_info}")
    if not user_info:
        return RedirectResponse(url="/login?error=no_user_info", status_code=302)

    email = user_info.get("email")
    if not email:
        return RedirectResponse(url="/login?error=no_email", status_code=302)

    # Check if email is in allowed list
    allowed_emails = load_allowed_emails()
    if email not in allowed_emails:
        logger.warning(f"Unauthorized login attempt: {email}")
        return RedirectResponse(url="/login?error=unauthorized", status_code=302)

    # Create session and redirect to dashboard using intermediate HTML page.
    # WORKAROUND: Browsers may not persist cookies set during OAuth redirects
    # (cross-site navigation with SameSite=Lax). Using JavaScript to set the cookie
    # client-side ensures it persists. The token is signed with SESSION_SECRET_KEY
    # via itsdangerous, so tampering is detected on verification.
    session_token = create_session_token(email)
    logger.info(f"User logged in: {email}")

    max_age = SESSION_MAX_AGE_DAYS * 24 * 60 * 60
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Connexion en cours...</title>
    </head>
    <body>
        <p>Connexion en cours, veuillez patienter...</p>
        <script>
            document.cookie = "{SESSION_COOKIE_NAME}={session_token}; path=/; max-age={max_age}; SameSite=Lax";
            window.location.href = "/";
        </script>
        <noscript>
            <meta http-equiv="refresh" content="0;url=/">
        </noscript>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@router.post("/logout")
async def logout(request: Request):
    """Logout and clear session."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response
