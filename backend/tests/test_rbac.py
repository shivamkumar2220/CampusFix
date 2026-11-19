"""Tests for role-based access control (RBAC) enforced by the backend."""

from typing import Callable

import pytest
from fastapi.testclient import TestClient

from app.services import complaint_service, user_service

STUDENT_ID = 4
STAFF_ID = 2
ADMIN_ID = 1


def test_request_without_token_returns_401(api_client: TestClient) -> None:
    """Protected routes need a token."""
    response = api_client.get("/api/complaints/assigned")
    assert response.status_code == 401


def test_request_with_fake_token_returns_401(api_client: TestClient) -> None:
    """A made-up token is rejected because its signature is wrong."""
    response = api_client.get(
        "/api/complaints/assigned", headers={"Authorization": "Bearer this.is.fake"}
    )
    assert response.status_code == 401


def test_student_cannot_access_staff_route(
    api_client: TestClient, fake_user_lookup: None, auth_header_for: Callable[[int], dict]
) -> None:
    """A student calling the staff-only complaint list gets 403 Forbidden."""
    response = api_client.get("/api/complaints/assigned", headers=auth_header_for(STUDENT_ID))
    assert response.status_code == 403
    assert "staff" in response.json()["detail"]


def test_student_cannot_change_complaint_status(
    api_client: TestClient, fake_user_lookup: None, auth_header_for: Callable[[int], dict]
) -> None:
    """Students cannot use the staff status endpoint, even if they know the URL."""
    response = api_client.patch(
        "/api/complaints/1/status",
        json={"new_status": "Resolved"},
        headers=auth_header_for(STUDENT_ID),
    )
    assert response.status_code == 403


def test_student_cannot_access_admin_user_management(
    api_client: TestClient, fake_user_lookup: None, auth_header_for: Callable[[int], dict]
) -> None:
    """User management is admin only."""
    response = api_client.get("/api/users", headers=auth_header_for(STUDENT_ID))
    assert response.status_code == 403


def test_staff_cannot_access_admin_dashboard(
    api_client: TestClient, fake_user_lookup: None, auth_header_for: Callable[[int], dict]
) -> None:
    """Staff can manage complaints but cannot see admin statistics."""
    response = api_client.get("/api/dashboard/stats", headers=auth_header_for(STAFF_ID))
    assert response.status_code == 403


def test_staff_cannot_create_complaint(
    api_client: TestClient, fake_user_lookup: None, auth_header_for: Callable[[int], dict]
) -> None:
    """Only students report complaints."""
    response = api_client.post(
        "/api/complaints",
        json={"title": "Wi-Fi down", "description": "Wi-Fi is down in Lab 3", "location": "Lab 3"},
        headers=auth_header_for(STAFF_ID),
    )
    assert response.status_code == 403


def test_staff_can_access_staff_route(
    api_client: TestClient,
    fake_user_lookup: None,
    auth_header_for: Callable[[int], dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staff are allowed through, and only their own team is requested."""
    received_arguments = {}

    def fake_get_complaints_for_staff(user: dict, *filters: object) -> list:
        """Remember who asked and return an empty list instead of querying the database."""
        received_arguments["user"] = user
        return []

    monkeypatch.setattr(complaint_service, "get_complaints_for_staff", fake_get_complaints_for_staff)
    response = api_client.get("/api/complaints/assigned", headers=auth_header_for(STAFF_ID))
    assert response.status_code == 200
    assert response.json() == []
    assert received_arguments["user"]["team"] == "IT"


def test_admin_can_access_user_management(
    api_client: TestClient,
    fake_user_lookup: None,
    auth_header_for: Callable[[int], dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admins are allowed to list users."""
    monkeypatch.setattr(user_service, "get_all_users", lambda: [])
    response = api_client.get("/api/users", headers=auth_header_for(ADMIN_ID))
    assert response.status_code == 200


def test_student_can_only_view_own_complaint() -> None:
    """The access rule: students see only their own complaints, staff only their team's."""
    complaint = {"student_id": 4, "assigned_team": "IT"}
    owner_student = {"id": 4, "role": "student", "team": None}
    other_student = {"id": 5, "role": "student", "team": None}
    it_staff = {"id": 2, "role": "staff", "team": "IT"}
    maintenance_staff = {"id": 3, "role": "staff", "team": "Maintenance"}
    admin = {"id": 1, "role": "admin", "team": None}

    assert complaint_service.user_can_view_complaint(owner_student, complaint) is True
    assert complaint_service.user_can_view_complaint(other_student, complaint) is False
    assert complaint_service.user_can_view_complaint(it_staff, complaint) is True
    assert complaint_service.user_can_view_complaint(maintenance_staff, complaint) is False
    assert complaint_service.user_can_view_complaint(admin, complaint) is True
