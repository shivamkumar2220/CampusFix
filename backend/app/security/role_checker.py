"""FastAPI dependencies that protect routes: who is logged in, and are they allowed?

Usage in a route:
    current_user: dict = Depends(get_current_user)                 # any logged-in user
    current_user: dict = Depends(require_roles("staff", "admin"))  # only staff or admin
"""

from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.jwt_tokens import decode_access_token
from app.services.user_service import get_user_by_id

# Reads the "Authorization: Bearer <token>" header (and adds the Authorize button in /docs)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Return the logged-in user from the JWT in the Authorization header, or raise 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in. Send the header 'Authorization: Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_payload = decode_access_token(credentials.credentials)

    # Load the user from the database so role changes and deactivation apply immediately
    user = get_user_by_id(int(token_payload["sub"]))
    if user is None or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str) -> Callable[..., dict]:
    """Build a dependency that only lets users with one of the allowed roles through (else 403)."""

    def check_user_role(current_user: dict = Depends(get_current_user)) -> dict:
        """Raise 403 Forbidden if the logged-in user's role is not allowed."""
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. This action requires role: {', '.join(allowed_roles)}.",
            )
        return current_user

    return check_user_role
