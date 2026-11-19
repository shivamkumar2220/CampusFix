"""Shared test setup.

These tests do NOT need PostgreSQL: wherever the code would read the database,
we replace that one function with a fake version using pytest's monkeypatch.
"""

import os
from datetime import datetime, timezone
from typing import Callable

# Must be set before the app is imported: no background scheduler during tests
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import role_checker
from app.security.jwt_tokens import create_access_token

FAKE_USERS: dict[int, dict] = {
    1: {"id": 1, "full_name": "Test Admin", "email": "admin@test.edu", "role": "admin",
        "team": None, "is_active": True, "created_at": datetime.now(timezone.utc)},
    2: {"id": 2, "full_name": "Test IT Staff", "email": "it@test.edu", "role": "staff",
        "team": "IT", "is_active": True, "created_at": datetime.now(timezone.utc)},
    4: {"id": 4, "full_name": "Test Student", "email": "student@test.edu", "role": "student",
        "team": None, "is_active": True, "created_at": datetime.now(timezone.utc)},
}


@pytest.fixture
def api_client() -> TestClient:
    """A test client that sends requests to the app without starting a real server."""
    return TestClient(app)


@pytest.fixture
def fake_user_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make get_current_user load users from FAKE_USERS instead of the database."""
    monkeypatch.setattr(role_checker, "get_user_by_id", lambda user_id: FAKE_USERS.get(user_id))


@pytest.fixture
def auth_header_for() -> Callable[[int], dict]:
    """Return a helper that builds an Authorization header for one of the FAKE_USERS."""

    def build_auth_header(user_id: int) -> dict:
        """Create a real JWT for the fake user and wrap it in a header."""
        token = create_access_token(user_id, FAKE_USERS[user_id]["role"])
        return {"Authorization": f"Bearer {token}"}

    return build_auth_header
