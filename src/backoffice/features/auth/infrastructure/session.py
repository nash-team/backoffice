"""Session management using itsdangerous for signed cookies."""

import os
from datetime import datetime, timedelta

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE_DAYS = 30


def get_serializer() -> URLSafeTimedSerializer:
    """Get the session serializer with secret key from environment."""
    secret_key = os.getenv("SESSION_SECRET_KEY")
    if not secret_key:
        raise ValueError("SESSION_SECRET_KEY environment variable is required")
    return URLSafeTimedSerializer(secret_key)


def create_session_token(email: str) -> str:
    """Create a signed session token for the given email."""
    serializer = get_serializer()
    data = {
        "email": email,
        "created_at": datetime.utcnow().isoformat(),
    }
    token: str = serializer.dumps(data)
    return token


def verify_session_token(token: str) -> dict | None:
    """
    Verify a session token and return the session data.
    Returns None if token is invalid or expired.
    """
    serializer = get_serializer()
    max_age_seconds = SESSION_MAX_AGE_DAYS * 24 * 60 * 60

    try:
        data: dict = serializer.loads(token, max_age=max_age_seconds)
        return data
    except SignatureExpired:
        return None
    except BadSignature:
        return None


def get_session_expiry() -> datetime:
    """Get the expiry datetime for a new session."""
    return datetime.utcnow() + timedelta(days=SESSION_MAX_AGE_DAYS)
