"""Admin routes for managing users and roles."""

from fastapi import APIRouter, Depends, status

from app.schemas.user_schemas import (
    AdminCreateUserRequest,
    UpdateUserActiveRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from app.security.role_checker import require_roles
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["User Management (Admin)"])

admin_only = require_roles("admin")


@router.get("", response_model=list[UserResponse])
def list_users(current_user: dict = Depends(admin_only)) -> list[dict]:
    """Admin: list every user."""
    return user_service.get_all_users()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(new_user: AdminCreateUserRequest, current_user: dict = Depends(admin_only)) -> dict:
    """Admin: create a user with any role (e.g. a new staff member)."""
    return user_service.create_user(
        new_user.full_name, new_user.email, new_user.password, new_user.role, new_user.team
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: int,
    role_update: UpdateUserRoleRequest,
    current_user: dict = Depends(admin_only),
) -> dict:
    """Admin: change a user's role and team."""
    return user_service.update_user_role(user_id, role_update.role, role_update.team, current_user["id"])


@router.patch("/{user_id}/active", response_model=UserResponse)
def change_user_active(
    user_id: int,
    active_update: UpdateUserActiveRequest,
    current_user: dict = Depends(admin_only),
) -> dict:
    """Admin: activate or deactivate a user account."""
    return user_service.set_user_active(user_id, active_update.is_active, current_user["id"])
