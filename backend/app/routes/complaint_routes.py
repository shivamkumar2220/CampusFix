"""Routes for complaints. Each route only reads the request, calls a service, and returns the result.

Fixed paths like /my and /assigned are declared BEFORE /{complaint_id} so FastAPI matches them first.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.constants import CategoryName, ComplaintStatus, PriorityLevel, TeamName
from app.schemas.complaint_schemas import (
    CommentResponse,
    ComplaintCreatedResponse,
    ComplaintCreateRequest,
    ComplaintResponse,
    GroupIncidentRequest,
    HistoryEntryResponse,
    MessageRequest,
    PriorityOverrideRequest,
    ReopenRequest,
    SimilarComplaintResponse,
    StatusUpdateRequest,
)
from app.security.role_checker import get_current_user, require_roles
from app.services import complaint_service

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

# Reusable role dependencies
student_only = require_roles("student")
staff_or_admin = require_roles("staff", "admin")
admin_only = require_roles("admin")


# ----------------------------- Student -----------------------------

@router.post("", response_model=ComplaintCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(
    complaint_request: ComplaintCreateRequest,
    current_user: dict = Depends(student_only),
) -> dict:
    """Student: report a new issue. Category, priority and team are filled in automatically."""
    return complaint_service.create_complaint(complaint_request, current_user)


@router.get("/my", response_model=list[ComplaintResponse])
def get_my_complaints(current_user: dict = Depends(student_only)) -> list[dict]:
    """Student: list ONLY my own complaints."""
    return complaint_service.get_complaints_for_student(current_user["id"])


# --------------------------- Staff / Admin ---------------------------

@router.get("/assigned", response_model=list[ComplaintResponse])
def get_assigned_complaints(
    status_filter: Optional[ComplaintStatus] = Query(default=None, alias="status"),
    priority_filter: Optional[PriorityLevel] = Query(default=None, alias="priority"),
    category_filter: Optional[CategoryName] = Query(default=None, alias="category"),
    current_user: dict = Depends(staff_or_admin),
) -> list[dict]:
    """Staff: complaints assigned to my team (admin: all complaints). Optional filters."""
    return complaint_service.get_complaints_for_staff(
        current_user, status_filter, priority_filter, category_filter
    )


# ------------------------------ Admin ------------------------------

@router.get("", response_model=list[ComplaintResponse])
def get_all_complaints(
    status_filter: Optional[ComplaintStatus] = Query(default=None, alias="status"),
    priority_filter: Optional[PriorityLevel] = Query(default=None, alias="priority"),
    category_filter: Optional[CategoryName] = Query(default=None, alias="category"),
    team_filter: Optional[TeamName] = Query(default=None, alias="team"),
    current_user: dict = Depends(admin_only),
) -> list[dict]:
    """Admin: every complaint in the system, with optional filters."""
    return complaint_service.get_complaints_with_filters({
        "status": status_filter,
        "priority": priority_filter,
        "category": category_filter,
        "assigned_team": team_filter,
    })


@router.get("/escalated", response_model=list[ComplaintResponse])
def get_escalated_complaints(current_user: dict = Depends(admin_only)) -> list[dict]:
    """Admin: complaints that breached their SLA and were escalated."""
    return complaint_service.get_escalated_complaints()


# --------------------------- One complaint ---------------------------

@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(complaint_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    """Any role: one complaint (students only their own, staff only their team's)."""
    return complaint_service.get_complaint_for_user(complaint_id, current_user)


@router.get("/{complaint_id}/history", response_model=list[HistoryEntryResponse])
def get_complaint_history(complaint_id: int, current_user: dict = Depends(get_current_user)) -> list[dict]:
    """Any role: the status timeline of a complaint."""
    return complaint_service.get_complaint_history(complaint_id, current_user)


@router.get("/{complaint_id}/comments", response_model=list[CommentResponse])
def get_complaint_comments(complaint_id: int, current_user: dict = Depends(get_current_user)) -> list[dict]:
    """Any role: comments on a complaint (internal staff notes are hidden from students)."""
    return complaint_service.get_complaint_comments(complaint_id, current_user)


@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
def update_status(
    complaint_id: int,
    status_update: StatusUpdateRequest,
    current_user: dict = Depends(staff_or_admin),
) -> dict:
    """Staff/Admin: move the complaint along the status flow."""
    return complaint_service.update_complaint_status(
        complaint_id, status_update.new_status, status_update.note, current_user
    )


@router.patch("/{complaint_id}/priority", response_model=ComplaintResponse)
def override_priority(
    complaint_id: int,
    priority_override: PriorityOverrideRequest,
    current_user: dict = Depends(staff_or_admin),
) -> dict:
    """Staff/Admin: replace the suggested priority."""
    return complaint_service.override_priority(
        complaint_id, priority_override.priority, priority_override.reason, current_user
    )


@router.post("/{complaint_id}/request-info", response_model=ComplaintResponse)
def request_more_information(
    complaint_id: int,
    info_request: MessageRequest,
    current_user: dict = Depends(staff_or_admin),
) -> dict:
    """Staff/Admin: ask the student a question (status -> Need More Info)."""
    return complaint_service.request_more_information(complaint_id, info_request.message, current_user)


@router.post("/{complaint_id}/notes", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_staff_note(
    complaint_id: int,
    note: MessageRequest,
    current_user: dict = Depends(staff_or_admin),
) -> dict:
    """Staff/Admin: add an internal note (hidden from the student)."""
    return complaint_service.add_staff_note(complaint_id, note.message, current_user)


@router.get("/{complaint_id}/similar", response_model=list[SimilarComplaintResponse])
def get_similar_complaints(complaint_id: int, current_user: dict = Depends(staff_or_admin)) -> list[dict]:
    """Staff/Admin: other open complaints with the same category and location."""
    return complaint_service.get_similar_complaints_for_complaint(complaint_id, current_user)


@router.post("/{complaint_id}/group", response_model=ComplaintResponse)
def group_into_incident(
    complaint_id: int,
    group_request: GroupIncidentRequest,
    current_user: dict = Depends(staff_or_admin),
) -> dict:
    """Staff/Admin: confirm this complaint is part of the same incident as another one."""
    return complaint_service.group_into_incident(
        complaint_id, group_request.parent_complaint_id, current_user
    )


@router.post("/{complaint_id}/reply", response_model=ComplaintResponse)
def reply_to_information_request(
    complaint_id: int,
    reply: MessageRequest,
    current_user: dict = Depends(student_only),
) -> dict:
    """Student: answer the staff's question (status -> In Progress)."""
    return complaint_service.reply_to_information_request(complaint_id, reply.message, current_user)


@router.post("/{complaint_id}/confirm", response_model=ComplaintResponse)
def confirm_resolution(complaint_id: int, current_user: dict = Depends(student_only)) -> dict:
    """Student: confirm the fix works (Resolved -> Closed)."""
    return complaint_service.confirm_resolution(complaint_id, current_user)


@router.post("/{complaint_id}/reopen", response_model=ComplaintResponse)
def reopen_complaint(
    complaint_id: int,
    reopen_request: ReopenRequest,
    current_user: dict = Depends(student_only),
) -> dict:
    """Student: the problem is not fixed (Resolved -> Open)."""
    return complaint_service.reopen_complaint(complaint_id, reopen_request.reason, current_user)
