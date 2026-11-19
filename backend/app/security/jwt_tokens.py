"""Creating and verifying JWT access tokens."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import settings


def create_access_token(user_id: int, role: str) -> str:
    """Create a signed JWT that says who the user is, their role, and when it expires."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    token_payload = {
        "sub": str(user_id),  # "subject" = the user this token belongs to
        "role": role,
        "exp": expires_at,     # python-jose rejects the token automatically after this time
    }
    return jwt.encode(token_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Verify the token signature and expiry, and return its payload.

    Raises 401 Unauthorized when the token is fake, changed, or expired.
    """
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
