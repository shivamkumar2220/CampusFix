"""Pydantic models for the admin dashboard."""

from typing import Optional

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    """Simple numbers shown on the admin dashboard cards."""

    total_complaints: int
    open_complaints: int
    escalated_complaints: int
    resolved_or_closed_complaints: int
    total_users: int
    average_resolution_hours: Optional[float] = None
    complaints_by_status: dict[str, int]
    complaints_by_priority: dict[str, int]
    complaints_by_category: dict[str, int]
    complaints_by_team: dict[str, int]


class SlaCheckResponse(BaseModel):
    """Result of one run of the SLA escalation check."""

    complaints_checked: int
    reminders_sent: int
    complaints_escalated: int


class MessageResponse(BaseModel):
    """A simple confirmation message."""

    message: str
