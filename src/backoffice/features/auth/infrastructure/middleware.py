"""Authentication middleware for protecting routes."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from backoffice.features.auth.infrastructure.session import (
    SESSION_COOKIE_NAME,
    verify_session_token,
)

logger = logging.getLogger(__name__)

# Routes that don't require authentication
PUBLIC_PATHS = [
    "/login",
    "/auth/google",
    "/auth/google/callback",
    "/logout",
    "/static",
    "/healthz",
    "/__test__",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that redirects unauthenticated users to login page."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public paths
        for public_path in PUBLIC_PATHS:
            if path.startswith(public_path):
                return await call_next(request)

        # Check for session cookie
        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        logger.info(f"[AuthMiddleware] Path: {path}, Cookie present: {bool(session_token)}")

        if not session_token:
            logger.info("[AuthMiddleware] No session cookie, redirecting to login")
            return RedirectResponse(url="/login", status_code=302)

        # Verify session token
        session_data = verify_session_token(session_token)
        logger.info(f"[AuthMiddleware] Session data: {session_data}")

        if session_data is None:
            # Session expired or invalid
            logger.info("[AuthMiddleware] Session invalid/expired, redirecting to login")
            response = RedirectResponse(url="/login?error=session_expired", status_code=302)
            response.delete_cookie(key=SESSION_COOKIE_NAME)
            return response

        # Session valid, continue
        return await call_next(request)
