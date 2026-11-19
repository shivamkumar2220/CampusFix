"""Routes for registering, logging in, and checking who is logged in."""

from fastapi import APIRouter, Depends, status

from app.schemas.user_schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.security.role_checker import get_current_user
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(registration: UserRegisterRequest) -> dict:
    """Create a new STUDENT account (anyone can call this)."""
    return auth_service.register_student(registration)


@router.post("/login", response_model=TokenResponse)
def login(login_request: UserLoginRequest) -> dict:
    """Log in with email + password and receive a JWT access token."""
    return auth_service.login_user(login_request.email, login_request.password)


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: dict = Depends(get_current_user)) -> dict:
    """Return the logged-in user's own details."""
    return current_user
