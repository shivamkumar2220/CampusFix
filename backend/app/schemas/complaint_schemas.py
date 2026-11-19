"""Pydantic models for complaints, their history and comments."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.constants import CategoryName, ComplaintStatus, PriorityLevel, TeamName


class ComplaintCreateRequest(BaseModel):
    """What a student types in the 'New Complaint' form."""

    title: str = Field(min_length=5, max_length=150, examples=["Wi-Fi not working in Lab 3"])
    description: str = Field(
        min_length=10,
        max_length=2000,
        examples=["The Wi-Fi in Lab 3 keeps disconnecting. We have a lab exam tomorrow, urgent."],
    )
    location: str = Field(min_length=2, max_length=100, examples=["Lab 3"])


class ComplaintResponse(BaseModel):
    """A complaint as returned by the API."""

    id: int
    title: str
    description: str
    location: str
    category: CategoryName
    priority: PriorityLevel
    suggested_priority: PriorityLevel
    status: ComplaintStatus
    assigned_team: TeamName
    student_id: int
    student_name: Optional[str] = None
    is_possible_common_incident: bool
    incident_group_id: Optional[int] = None
    sla_due_at: datetime
    reminder_sent_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ComplaintCreatedResponse(BaseModel):
    """Returned after creating a complaint: the complaint plus what the system detected."""

    complaint: ComplaintResponse
    similar_open_complaints_count: int
    message: str


class StatusUpdateRequest(BaseModel):
    """Staff change the status of a complaint."""

    new_status: ComplaintStatus = Field(examples=["In Progress"])
    note: Optional[str] = Field(default=None, max_length=1000, examples=["Technician sent to Lab 3"])


class PriorityOverrideRequest(BaseModel):
    """Staff replace the suggested priority with their own choice."""

    priority: PriorityLevel = Field(examples=["High"])
    reason: str = Field(min_length=3, max_length=500, examples=["Whole floor affected"])


class MessageRequest(BaseModel):
    """A short text message (request for info, reply, or staff note)."""

    message: str = Field(min_length=2, max_length=1000, examples=["Which computer number is broken?"])


class ReopenRequest(BaseModel):
    """Student explains why the fix did not work."""

    reason: str = Field(min_length=3, max_length=1000, examples=["Wi-Fi is still disconnecting"])


class GroupIncidentRequest(BaseModel):
    """Staff confirm this complaint is part of the same incident as another complaint."""

    parent_complaint_id: int = Field(gt=0, examples=[1])


class SimilarComplaintResponse(BaseModel):
    """A short summary of a similar open complaint (same category + location)."""

    id: int
    title: str
    status: ComplaintStatus
    priority: PriorityLevel
    location: str
    incident_group_id: Optional[int] = None
    created_at: datetime


class HistoryEntryResponse(BaseModel):
    """One line of the complaint's timeline."""

    id: int
    complaint_id: int
    changed_by: Optional[int] = None
    changed_by_name: Optional[str] = None
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime


class CommentResponse(BaseModel):
    """A comment or note on a complaint."""

    id: int
    complaint_id: int
    author_id: int
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    comment_type: str
    message: str
    is_internal: bool
    created_at: datetime
