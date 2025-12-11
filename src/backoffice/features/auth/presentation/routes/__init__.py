"""Authentication routes for Google OAuth."""

import os
from pathlib import Path

import yaml
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from backoffice.features.auth.infrastructure.session import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_DAYS,
    create_session_token,
)
from backoffice.features.shared.presentation.routes.templates import templates

router = APIRouter(tags=["auth"])

# Initialize OAuth client
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
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
    except Exception:
        return RedirectResponse(url="/login?error=auth_failed", status_code=302)

    user_info = token.get("userinfo")
    if not user_info:
        return RedirectResponse(url="/login?error=no_user_info", status_code=302)

    email = user_info.get("email")
    if not email:
        return RedirectResponse(url="/login?error=no_email", status_code=302)

    # Check if email is in allowed list
    allowed_emails = load_allowed_emails()
    if email not in allowed_emails:
        return RedirectResponse(url="/login?error=unauthorized", status_code=302)

    # Create session and redirect to dashboard
    session_token = create_session_token(email)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_MAX_AGE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    """Logout and clear session."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response
