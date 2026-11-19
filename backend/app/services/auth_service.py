"""Registration and login logic."""

from fastapi import HTTPException, status

from app.schemas.user_schemas import UserRegisterRequest
from app.security.jwt_tokens import create_access_token
from app.security.password_hashing import verify_password
from app.services.user_service import create_user, get_user_by_email_with_password


def register_student(registration: UserRegisterRequest) -> dict:
    """Create a new student account. Public registration can never create staff or admins."""
    return create_user(
        full_name=registration.full_name,
        email=registration.email,
        password=registration.password,
        role="student",
        team=None,
    )


def remove_password_hash(user_row: dict) -> dict:
    """Return a copy of the user without the password hash, so it is never sent to the browser."""
    return {key: value for key, value in user_row.items() if key != "password_hash"}


def login_user(email: str, password: str) -> dict:
    """Check email + password and return a JWT access token plus the user's details."""
    user = get_user_by_email_with_password(email)

    # Same message for "no such email" and "wrong password", so attackers cannot guess emails
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact the admin.",
        )

    return {
        "access_token": create_access_token(user["id"], user["role"]),
        "token_type": "bearer",
        "user": remove_password_hash(user),
    }
