"""Everything about user accounts: loading, creating, changing role, activating."""

from typing import Optional

from fastapi import HTTPException, status

from app.database import fetch_all_rows, fetch_one_row
from app.security.password_hashing import hash_password

# Columns that are safe to return (password_hash is deliberately missing)
PUBLIC_USER_COLUMNS = "id, full_name, email, role, team, is_active, created_at"


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Return a user (without password hash) or None if the id does not exist."""
    return fetch_one_row(f"SELECT {PUBLIC_USER_COLUMNS} FROM users WHERE id = %s", (user_id,))


def get_user_by_email_with_password(email: str) -> Optional[dict]:
    """Return a user INCLUDING the password hash. Only used by the login check."""
    return fetch_one_row("SELECT * FROM users WHERE email = %s", (email.lower(),))


def is_email_taken(email: str) -> bool:
    """Check whether an account with this email already exists."""
    return fetch_one_row("SELECT id FROM users WHERE email = %s", (email.lower(),)) is not None


def decide_team_for_role(role: str, team: Optional[str]) -> Optional[str]:
    """Staff must have a team, students never have one, admins may have one."""
    if role == "staff" and team is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Staff users must belong to a team (IT or Maintenance).",
        )
    if role == "student":
        return None
    return team


def create_user(full_name: str, email: str, password: str, role: str, team: Optional[str]) -> dict:
    """Create a new user with a hashed password and return it (without the hash)."""
    if is_email_taken(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    return fetch_one_row(
        f"""
        INSERT INTO users (full_name, email, password_hash, role, team)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING {PUBLIC_USER_COLUMNS}
        """,
        (full_name.strip(), email.lower(), hash_password(password), role, decide_team_for_role(role, team)),
    )


def get_all_users() -> list[dict]:
    """Return every user, grouped by role, for the admin user-management table."""
    return fetch_all_rows(f"SELECT {PUBLIC_USER_COLUMNS} FROM users ORDER BY role, full_name")


def get_user_or_404(user_id: int) -> dict:
    """Return a user or raise 404 Not Found."""
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def prevent_admin_changing_own_account(target_user_id: int, acting_admin_id: int) -> None:
    """Stop an admin from demoting or deactivating themselves and getting locked out."""
    if target_user_id == acting_admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role or deactivate your own account.",
        )


def update_user_role(user_id: int, role: str, team: Optional[str], acting_admin_id: int) -> dict:
    """Change a user's role and team (admin only)."""
    get_user_or_404(user_id)
    prevent_admin_changing_own_account(user_id, acting_admin_id)
    return fetch_one_row(
        f"UPDATE users SET role = %s, team = %s WHERE id = %s RETURNING {PUBLIC_USER_COLUMNS}",
        (role, decide_team_for_role(role, team), user_id),
    )


def set_user_active(user_id: int, is_active: bool, acting_admin_id: int) -> dict:
    """Activate or deactivate a user account (admin only)."""
    get_user_or_404(user_id)
    prevent_admin_changing_own_account(user_id, acting_admin_id)
    return fetch_one_row(
        f"UPDATE users SET is_active = %s WHERE id = %s RETURNING {PUBLIC_USER_COLUMNS}",
        (is_active, user_id),
    )
