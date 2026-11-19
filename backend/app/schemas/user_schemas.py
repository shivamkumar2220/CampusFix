"""Pydantic models for users and login. They validate input and shape the output.

Note: no response model has a password or password_hash field, so it can never leak.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.constants import RoleName, TeamName


class UserRegisterRequest(BaseModel):
    """Data a student sends to create their own account."""

    full_name: str = Field(min_length=2, max_length=100, examples=["Riya Sharma"])
    email: EmailStr = Field(examples=["riya@campusfix.edu"])
    password: str = Field(min_length=8, max_length=72, examples=["Student@123"])


class UserLoginRequest(BaseModel):
    """Email and password sent to the login endpoint."""

    email: EmailStr = Field(examples=["student1@campusfix.edu"])
    password: str = Field(min_length=1, max_length=72, examples=["Student@123"])


class UserResponse(BaseModel):
    """Public information about a user (safe to send to the browser)."""

    id: int
    full_name: str
    email: EmailStr
    role: RoleName
    team: Optional[TeamName] = None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """Returned after a successful login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminCreateUserRequest(BaseModel):
    """Data an admin sends to create any kind of user (e.g. a new staff member)."""

    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: RoleName
    team: Optional[TeamName] = None


class UpdateUserRoleRequest(BaseModel):
    """Change a user's role (and team, which staff must have)."""

    role: RoleName
    team: Optional[TeamName] = None


class UpdateUserActiveRequest(BaseModel):
    """Activate or deactivate a user account."""

    is_active: bool
