"""Tests for the SLA rules and the escalation job (no database needed)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services import sla_service
from app.services.complaint_service import is_valid_staff_transition
from app.services.similarity_service import normalize_location
from app.services.sla_service import (
    SLA_ACTION_ESCALATE,
    SLA_ACTION_NONE,
    SLA_ACTION_SEND_REMINDER,
    calculate_sla_due_time,
    decide_sla_action,
)

NOW = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("priority", "expected_hours"),
    [("Critical", 4), ("High", 24), ("Medium", 48), ("Low", 72)],
)
def test_sla_due_time_per_priority(priority: str, expected_hours: int) -> None:
    """Each priority gets its own time limit."""
    assert calculate_sla_due_time(priority, NOW) == NOW + timedelta(hours=expected_hours)


def test_no_action_before_deadline() -> None:
    """Nothing happens while the complaint is still within its SLA."""
    assert decide_sla_action(NOW + timedelta(hours=1), None, NOW) == SLA_ACTION_NONE


def test_first_breach_sends_reminder() -> None:
    """Past the deadline without a reminder -> send a reminder first."""
    assert decide_sla_action(NOW - timedelta(minutes=5), None, NOW) == SLA_ACTION_SEND_REMINDER


def test_still_overdue_after_reminder_escalates() -> None:
    """Past the deadline and already reminded -> escalate."""
    reminder_time = NOW - timedelta(minutes=15)
    assert decide_sla_action(NOW - timedelta(hours=1), reminder_time, NOW) == SLA_ACTION_ESCALATE


def test_check_sla_and_escalate_runs_the_right_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """The job reminds the first complaint and escalates the second one."""
    overdue_complaints = [
        {"id": 1, "sla_due_at": NOW - timedelta(hours=1), "reminder_sent_at": None},
        {"id": 2, "sla_due_at": NOW - timedelta(hours=2), "reminder_sent_at": NOW - timedelta(minutes=15)},
    ]
    reminded_ids: list[int] = []
    escalated_ids: list[int] = []

    monkeypatch.setattr(sla_service, "get_overdue_complaints", lambda current_time: overdue_complaints)
    monkeypatch.setattr(sla_service, "send_sla_reminder", lambda complaint: reminded_ids.append(complaint["id"]))
    monkeypatch.setattr(sla_service, "escalate_complaint", lambda complaint: escalated_ids.append(complaint["id"]))

    summary = sla_service.check_sla_and_escalate(current_time=NOW)

    assert reminded_ids == [1]
    assert escalated_ids == [2]
    assert summary == {"complaints_checked": 2, "reminders_sent": 1, "complaints_escalated": 1}


def test_staff_status_flow_rules() -> None:
    """Open -> In Progress -> Resolved is allowed; skipping steps or closing is not."""
    assert is_valid_staff_transition("Open", "In Progress") is True
    assert is_valid_staff_transition("In Progress", "Resolved") is True
    assert is_valid_staff_transition("Escalated", "In Progress") is True
    assert is_valid_staff_transition("Open", "Resolved") is False
    assert is_valid_staff_transition("Resolved", "Closed") is False  # only the student closes


def test_location_normalization_for_similarity() -> None:
    """'  LAB   3 ' and 'lab 3' are treated as the same place."""
    assert normalize_location("  LAB   3 ") == normalize_location("lab 3") == "lab 3"
