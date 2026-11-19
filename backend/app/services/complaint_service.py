"""The complaint flow: create, list, change status/priority, request info, confirm, reopen, group.

Status flow:
    Open -> In Progress -> Resolved -> Closed            (student confirms the fix)
                                    -> Open              (student reopens it)
    Staff can set "Need More Info"; the student's reply moves it back to "In Progress".
    The SLA job can set "Escalated"; staff then continue with In Progress / Resolved.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.constants import (
    STATUS_CLOSED,
    STATUS_ESCALATED,
    STATUS_IN_PROGRESS,
    STATUS_NEED_MORE_INFO,
    STATUS_OPEN,
    STATUS_RESOLVED,
)
from app.database import execute_query, fetch_all_rows, fetch_one_row
from app.schemas.complaint_schemas import ComplaintCreateRequest
from app.services.classification_service import classify_complaint, get_team_for_category
from app.services.history_service import get_history_for_complaint, record_history
from app.services.notification_service import notify_team_staff, notify_users
from app.services.priority_service import suggest_priority
from app.services.similarity_service import (
    find_similar_open_complaints,
    mark_as_possible_common_incident,
)
from app.services.sla_service import calculate_sla_due_time

# Which status changes staff are allowed to make: current status -> allowed new statuses
STAFF_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    STATUS_OPEN: {STATUS_IN_PROGRESS, STATUS_NEED_MORE_INFO},
    STATUS_IN_PROGRESS: {STATUS_RESOLVED, STATUS_NEED_MORE_INFO},
    STATUS_NEED_MORE_INFO: {STATUS_IN_PROGRESS},
    STATUS_ESCALATED: {STATUS_IN_PROGRESS, STATUS_RESOLVED, STATUS_NEED_MORE_INFO},
}

# Base query used whenever we return complaints (adds the student's name)
COMPLAINT_SELECT_QUERY = """
    SELECT c.*, u.full_name AS student_name
    FROM complaints c
    JOIN users u ON u.id = c.student_id
"""

# Filters that list endpoints accept, mapped to their database column
ALLOWED_FILTER_COLUMNS = {
    "status": "c.status",
    "priority": "c.priority",
    "category": "c.category",
    "assigned_team": "c.assigned_team",
}


# ---------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------

def clean_location(location: str) -> str:
    """Remove extra spaces from a location, e.g. '  Lab   3 ' -> 'Lab 3'."""
    return " ".join(location.split())


def build_filter_clause(filters: dict[str, Optional[str]]) -> tuple[str, list]:
    """Turn {'status': 'Open', 'priority': None} into ('WHERE c.status = %s', ['Open'])."""
    conditions = []
    parameters = []
    for filter_name, filter_value in filters.items():
        if filter_value is not None and filter_name in ALLOWED_FILTER_COLUMNS:
            conditions.append(f"{ALLOWED_FILTER_COLUMNS[filter_name]} = %s")
            parameters.append(filter_value)
    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_clause, parameters


def is_valid_staff_transition(current_status: str, new_status: str) -> bool:
    """Check whether staff may move a complaint from current_status to new_status."""
    return new_status in STAFF_ALLOWED_TRANSITIONS.get(current_status, set())


def add_comment(
    complaint_id: int,
    author_id: int,
    comment_type: str,
    message: str,
    is_internal: bool = False,
) -> dict:
    """Save a comment (info request, reply, staff note, or reopen reason)."""
    return fetch_one_row(
        """
        INSERT INTO complaint_comments (complaint_id, author_id, comment_type, message, is_internal)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
        """,
        (complaint_id, author_id, comment_type, message.strip(), is_internal),
    )


# ---------------------------------------------------------------------
# Loading complaints + access checks
# ---------------------------------------------------------------------

def get_complaint_by_id(complaint_id: int) -> Optional[dict]:
    """Return one complaint (with the student's name) or None."""
    return fetch_one_row(COMPLAINT_SELECT_QUERY + " WHERE c.id = %s", (complaint_id,))


def get_complaint_or_404(complaint_id: int) -> dict:
    """Return one complaint or raise 404 Not Found."""
    complaint = get_complaint_by_id(complaint_id)
    if complaint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found.")
    return complaint


def user_can_view_complaint(user: dict, complaint: dict) -> bool:
    """Students see their own complaints, staff see their team's, admins see all."""
    if user["role"] == "admin":
        return True
    if user["role"] == "staff":
        return user["team"] == complaint["assigned_team"]
    return user["id"] == complaint["student_id"]


def get_complaint_for_user(complaint_id: int, user: dict) -> dict:
    """Return a complaint if this user is allowed to see it (404 / 403 otherwise)."""
    complaint = get_complaint_or_404(complaint_id)
    if not user_can_view_complaint(user, complaint):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this complaint.",
        )
    return complaint


def get_own_complaint_for_student(complaint_id: int, student: dict) -> dict:
    """Return a complaint only if it belongs to this student."""
    complaint = get_complaint_or_404(complaint_id)
    if complaint["student_id"] != student["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own complaints.",
        )
    return complaint


# ---------------------------------------------------------------------
# Creating a complaint (classification + similarity + priority + team + SLA)
# ---------------------------------------------------------------------

def create_complaint(complaint_request: ComplaintCreateRequest, student: dict) -> dict:
    """Create a complaint and run all the automatic rules on it."""
    location = clean_location(complaint_request.location)

    category = classify_complaint(complaint_request.title, complaint_request.description)
    assigned_team = get_team_for_category(category)
    similar_complaints = find_similar_open_complaints(category, location)
    suggested_priority = suggest_priority(
        category,
        complaint_request.title,
        complaint_request.description,
        location,
        len(similar_complaints),
    )
    sla_due_at = calculate_sla_due_time(suggested_priority, datetime.now(timezone.utc))

    new_complaint = fetch_one_row(
        """
        INSERT INTO complaints (title, description, location, category, priority,
                                suggested_priority, status, assigned_team, student_id, sla_due_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            complaint_request.title.strip(),
            complaint_request.description.strip(),
            location,
            category,
            suggested_priority,
            suggested_priority,
            STATUS_OPEN,
            assigned_team,
            student["id"],
            sla_due_at,
        ),
    )
    complaint_id = new_complaint["id"]

    if similar_complaints:
        mark_as_possible_common_incident([complaint_id] + [row["id"] for row in similar_complaints])

    record_history(
        complaint_id,
        student["id"],
        "created",
        new_value=STATUS_OPEN,
        note=f"Category: {category}. Suggested priority: {suggested_priority}. Assigned to {assigned_team} team.",
    )
    notify_team_staff(
        assigned_team,
        f"New {suggested_priority} complaint #{complaint_id}: {complaint_request.title} ({location})",
        complaint_id,
    )

    message = f"Complaint submitted and assigned to the {assigned_team} team."
    if similar_complaints:
        message += f" {len(similar_complaints)} similar open complaint(s) found - marked as a Possible Common Incident."

    return {
        "complaint": get_complaint_by_id(complaint_id),
        "similar_open_complaints_count": len(similar_complaints),
        "message": message,
    }


# ---------------------------------------------------------------------
# Listing complaints
# ---------------------------------------------------------------------

def get_complaints_for_student(student_id: int) -> list[dict]:
    """Return only the complaints created by this student, newest first."""
    return fetch_all_rows(
        COMPLAINT_SELECT_QUERY + " WHERE c.student_id = %s ORDER BY c.created_at DESC",
        (student_id,),
    )


def get_complaints_with_filters(filters: dict[str, Optional[str]]) -> list[dict]:
    """Return complaints matching the filters, most urgent and newest first."""
    where_clause, parameters = build_filter_clause(filters)
    query = f"""
        {COMPLAINT_SELECT_QUERY}
        {where_clause}
        ORDER BY CASE c.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END,
                 c.created_at DESC
    """
    return fetch_all_rows(query, parameters)


def get_complaints_for_staff(
    user: dict,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
) -> list[dict]:
    """Staff see complaints assigned to their team; admins see all complaints."""
    team_filter = None if user["role"] == "admin" else user["team"]
    return get_complaints_with_filters({
        "status": status_filter,
        "priority": priority_filter,
        "category": category_filter,
        "assigned_team": team_filter,
    })


def get_escalated_complaints() -> list[dict]:
    """Return every complaint that is currently escalated."""
    return get_complaints_with_filters({"status": STATUS_ESCALATED})


# ---------------------------------------------------------------------
# Staff actions
# ---------------------------------------------------------------------

def save_status_change(
    complaint: dict,
    new_status: str,
    changed_by: int,
    note: Optional[str],
    action: str = "status_changed",
) -> dict:
    """Update the status in the database, record the history and notify the student."""
    if new_status == STATUS_RESOLVED:
        resolved_at_sql = "NOW()"
    elif new_status == STATUS_OPEN:
        resolved_at_sql = "NULL"
    else:
        resolved_at_sql = "resolved_at"

    execute_query(
        f"UPDATE complaints SET status = %s, resolved_at = {resolved_at_sql}, updated_at = NOW() WHERE id = %s",
        (new_status, complaint["id"]),
    )
    record_history(complaint["id"], changed_by, action, complaint["status"], new_status, note)
    notify_users(
        [complaint["student_id"]],
        f"Your complaint #{complaint['id']} is now '{new_status}'.",
        complaint["id"],
    )
    return get_complaint_by_id(complaint["id"])


def update_complaint_status(complaint_id: int, new_status: str, note: Optional[str], user: dict) -> dict:
    """Staff/admin move a complaint to a new status, following the allowed flow."""
    complaint = get_complaint_for_user(complaint_id, user)

    if not is_valid_staff_transition(complaint["status"], new_status):
        allowed_statuses = sorted(STAFF_ALLOWED_TRANSITIONS.get(complaint["status"], set()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot change status from '{complaint['status']}' to '{new_status}'. "
                f"Allowed: {', '.join(allowed_statuses) if allowed_statuses else 'none (only the student can act now)'}."
            ),
        )

    if new_status == STATUS_NEED_MORE_INFO:
        if not note or len(note.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please write what information you need from the student.",
            )
        return request_more_information(complaint_id, note, user)

    return save_status_change(complaint, new_status, user["id"], note)


def override_priority(complaint_id: int, new_priority: str, reason: str, user: dict) -> dict:
    """Staff/admin replace the priority. The SLA deadline is recalculated from the creation time."""
    complaint = get_complaint_for_user(complaint_id, user)
    if complaint["priority"] == new_priority:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The complaint already has priority '{new_priority}'.",
        )

    new_sla_due_at = calculate_sla_due_time(new_priority, complaint["created_at"])
    execute_query(
        """
        UPDATE complaints
        SET priority = %s, sla_due_at = %s, reminder_sent_at = NULL, updated_at = NOW()
        WHERE id = %s
        """,
        (new_priority, new_sla_due_at, complaint_id),
    )
    record_history(complaint_id, user["id"], "priority_changed", complaint["priority"], new_priority, reason)
    return get_complaint_by_id(complaint_id)


def request_more_information(complaint_id: int, message: str, user: dict) -> dict:
    """Staff ask the student a question. Status becomes 'Need More Info'."""
    complaint = get_complaint_for_user(complaint_id, user)
    if not is_valid_staff_transition(complaint["status"], STATUS_NEED_MORE_INFO):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot request more information while the complaint is '{complaint['status']}'.",
        )

    add_comment(complaint_id, user["id"], "info_request", message)
    return save_status_change(
        complaint,
        STATUS_NEED_MORE_INFO,
        user["id"],
        note=message,
        action="info_requested",
    )


def add_staff_note(complaint_id: int, message: str, user: dict) -> dict:
    """Staff add an internal note (students cannot see it)."""
    get_complaint_for_user(complaint_id, user)
    return add_comment(complaint_id, user["id"], "staff_note", message, is_internal=True)


def get_similar_complaints_for_complaint(complaint_id: int, user: dict) -> list[dict]:
    """Staff view the other open complaints with the same category + location."""
    complaint = get_complaint_for_user(complaint_id, user)
    return find_similar_open_complaints(complaint["category"], complaint["location"], complaint_id)


def group_into_incident(complaint_id: int, parent_complaint_id: int, user: dict) -> dict:
    """Staff verify two complaints are the same incident and link them together."""
    if complaint_id == parent_complaint_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A complaint cannot be grouped under itself.",
        )
    complaint = get_complaint_for_user(complaint_id, user)
    parent_complaint = get_complaint_for_user(parent_complaint_id, user)

    # Always link to the main (root) complaint of the group
    root_complaint_id = parent_complaint["incident_group_id"] or parent_complaint["id"]
    if root_complaint_id == complaint_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That complaint is already grouped under this one.",
        )

    execute_query(
        """
        UPDATE complaints
        SET incident_group_id = %s, is_possible_common_incident = TRUE, updated_at = NOW()
        WHERE id = %s OR incident_group_id = %s
        """,
        (root_complaint_id, complaint_id, complaint_id),
    )
    execute_query(
        "UPDATE complaints SET is_possible_common_incident = TRUE WHERE id = %s",
        (root_complaint_id,),
    )
    record_history(
        complaint_id,
        user["id"],
        "grouped",
        old_value=str(complaint["incident_group_id"]) if complaint["incident_group_id"] else None,
        new_value=str(root_complaint_id),
        note=f"Verified as the same incident as complaint #{root_complaint_id}.",
    )
    return get_complaint_by_id(complaint_id)


# ---------------------------------------------------------------------
# Student actions
# ---------------------------------------------------------------------

def reply_to_information_request(complaint_id: int, message: str, student: dict) -> dict:
    """Student answers the staff question. Status goes back to 'In Progress'."""
    complaint = get_own_complaint_for_student(complaint_id, student)
    if complaint["status"] != STATUS_NEED_MORE_INFO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only reply when staff have asked for more information.",
        )

    add_comment(complaint_id, student["id"], "info_reply", message)
    updated_complaint = save_status_change(
        complaint, STATUS_IN_PROGRESS, student["id"], note=message, action="student_replied"
    )
    notify_team_staff(
        complaint["assigned_team"],
        f"Student replied on complaint #{complaint_id}: {complaint['title']}",
        complaint_id,
    )
    return updated_complaint


def confirm_resolution(complaint_id: int, student: dict) -> dict:
    """Student confirms the fix works. Status becomes 'Closed'."""
    complaint = get_own_complaint_for_student(complaint_id, student)
    if complaint["status"] != STATUS_RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only a 'Resolved' complaint can be confirmed and closed.",
        )

    updated_complaint = save_status_change(
        complaint, STATUS_CLOSED, student["id"], note="Student confirmed the fix.", action="confirmed"
    )
    notify_team_staff(
        complaint["assigned_team"],
        f"Complaint #{complaint_id} was confirmed fixed and closed by the student.",
        complaint_id,
    )
    return updated_complaint


def reopen_complaint(complaint_id: int, reason: str, student: dict) -> dict:
    """Student says the problem is not fixed. Status goes back to 'Open' with a fresh SLA."""
    complaint = get_own_complaint_for_student(complaint_id, student)
    if complaint["status"] != STATUS_RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only a 'Resolved' complaint can be reopened.",
        )

    new_sla_due_at = calculate_sla_due_time(complaint["priority"], datetime.now(timezone.utc))
    execute_query(
        """
        UPDATE complaints
        SET status = %s, resolved_at = NULL, sla_due_at = %s,
            reminder_sent_at = NULL, escalated_at = NULL, updated_at = NOW()
        WHERE id = %s
        """,
        (STATUS_OPEN, new_sla_due_at, complaint_id),
    )
    add_comment(complaint_id, student["id"], "reopen_reason", reason)
    record_history(complaint_id, student["id"], "reopened", complaint["status"], STATUS_OPEN, reason)
    notify_team_staff(
        complaint["assigned_team"],
        f"Complaint #{complaint_id} was reopened by the student: {reason}",
        complaint_id,
    )
    return get_complaint_by_id(complaint_id)


# ---------------------------------------------------------------------
# History and comments
# ---------------------------------------------------------------------

def get_complaint_history(complaint_id: int, user: dict) -> list[dict]:
    """Return the status timeline of a complaint the user may see."""
    get_complaint_for_user(complaint_id, user)
    return get_history_for_complaint(complaint_id)


def get_complaint_comments(complaint_id: int, user: dict) -> list[dict]:
    """Return comments; students do not see internal staff notes."""
    get_complaint_for_user(complaint_id, user)
    hide_internal_sql = "AND cc.is_internal = FALSE" if user["role"] == "student" else ""
    return fetch_all_rows(
        f"""
        SELECT cc.*, u.full_name AS author_name, u.role AS author_role
        FROM complaint_comments cc
        JOIN users u ON u.id = cc.author_id
        WHERE cc.complaint_id = %s {hide_internal_sql}
        ORDER BY cc.created_at, cc.id
        """,
        (complaint_id,),
    )
