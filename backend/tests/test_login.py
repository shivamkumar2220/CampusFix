"""Tests for login, password hashing and JWT tokens."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.security.jwt_tokens import create_access_token, decode_access_token
from app.security.password_hashing import hash_password, verify_password
from app.services import auth_service

TEST_PASSWORD = "Student@123"


@pytest.fixture
def fake_student_in_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend the database contains one student with a known password."""
    stored_student = {
        "id": 4,
        "full_name": "Test Student",
        "email": "student@test.edu",
        "password_hash": hash_password(TEST_PASSWORD),
        "role": "student",
        "team": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

    def find_fake_user_by_email(email: str) -> dict | None:
        """Return the stored student only for the matching email."""
        return stored_student if email == stored_student["email"] else None

    monkeypatch.setattr(auth_service, "get_user_by_email_with_password", find_fake_user_by_email)


def test_password_is_hashed_and_can_be_verified() -> None:
    """The hash is not the password, but verify_password still recognises it."""
    password_hash = hash_password(TEST_PASSWORD)
    assert password_hash != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, password_hash) is True
    assert verify_password("WrongPassword", password_hash) is False


def test_jwt_token_contains_user_id_and_role() -> None:
    """A created token can be decoded back to the same user id and role."""
    token = create_access_token(user_id=7, role="staff")
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "staff"


def test_login_success_returns_token_without_password_hash(
    api_client: TestClient, fake_student_in_database: None
) -> None:
    """Correct email and password give a token, and the password hash is never returned."""
    response = api_client.post(
        "/api/auth/login", json={"email": "student@test.edu", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["role"] == "student"
    assert "password_hash" not in body["user"]
    assert "password_hash" not in response.text


def test_login_with_wrong_password_returns_401(
    api_client: TestClient, fake_student_in_database: None
) -> None:
    """A wrong password is rejected with 401 Unauthorized."""
    response = api_client.post(
        "/api/auth/login", json={"email": "student@test.edu", "password": "WrongPassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_login_with_unknown_email_returns_401(
    api_client: TestClient, fake_student_in_database: None
) -> None:
    """An email that does not exist gets the same 401 message (no hint for attackers)."""
    response = api_client.post(
        "/api/auth/login", json={"email": "nobody@test.edu", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401


def test_login_with_invalid_email_format_is_rejected_by_pydantic(api_client: TestClient) -> None:
    """Pydantic validation rejects a badly formatted email before any login logic runs."""
    response = api_client.post("/api/auth/login", json={"email": "not-an-email", "password": "x"})
    assert response.status_code == 422
