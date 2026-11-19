"""SLA (Service Level Agreement) checks and escalation. Rule-based, not AI.

Each priority has a time limit to fix the complaint:
    Critical 4 hours, High 24 hours, Medium 48 hours, Low 72 hours.

The background job calls check_sla_and_escalate() every 15 minutes:
    - past the limit, no reminder yet         -> send a reminder to the team
    - past the limit, reminder already sent   -> mark "Escalated" and notify admins
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.constants import STATUS_ESCALATED, STATUS_IN_PROGRESS, STATUS_OPEN
from app.database import execute_query, fetch_all_rows
from app.services.notification_service import notify_admins, notify_team_staff, notify_users
from app.services.history_service import record_history

SLA_HOURS_BY_PRIORITY: dict[str, int] = {
    "Critical": 4,
    "High": 24,
    "Medium": 48,
    "Low": 72,
}

# Only complaints waiting on staff are tracked ("Need More Info" waits on the student)
SLA_TRACKED_STATUSES = (STATUS_OPEN, STATUS_IN_PROGRESS)

SLA_ACTION_NONE = "none"
SLA_ACTION_SEND_REMINDER = "send_reminder"
SLA_ACTION_ESCALATE = "escalate"


def calculate_sla_due_time(priority: str, start_time: datetime) -> datetime:
    """Return the deadline for a complaint: start time + the hours allowed for its priority."""
    return start_time + timedelta(hours=SLA_HOURS_BY_PRIORITY[priority])


def decide_sla_action(
    sla_due_at: datetime,
    reminder_sent_at: Optional[datetime],
    current_time: datetime,
) -> str:
    """Decide what to do with one complaint: nothing, send a reminder, or escalate."""
    if current_time <= sla_due_at:
        return SLA_ACTION_NONE
    if reminder_sent_at is None:
        return SLA_ACTION_SEND_REMINDER
    return SLA_ACTION_ESCALATE


def get_overdue_complaints(current_time: datetime) -> list[dict]:
    """Load tracked complaints whose SLA deadline has passed and that are not escalated yet."""
    query = """
        SELECT id, title, priority, status, assigned_team, student_id, sla_due_at, reminder_sent_at
        FROM complaints
        WHERE status IN (%s, %s)
          AND escalated_at IS NULL
          AND sla_due_at < %s
        ORDER BY sla_due_at
    """
    return fetch_all_rows(query, (SLA_TRACKED_STATUSES[0], SLA_TRACKED_STATUSES[1], current_time))


def send_sla_reminder(complaint: dict) -> None:
    """Remind the assigned team that a complaint is past its SLA deadline."""
    execute_query("UPDATE complaints SET reminder_sent_at = NOW() WHERE id = %s", (complaint["id"],))
    record_history(
        complaint_id=complaint["id"],
        changed_by=None,
        action="sla_reminder",
        note=f"SLA deadline passed ({complaint['priority']} priority). Reminder sent to {complaint['assigned_team']} team.",
    )
    notify_team_staff(
        complaint["assigned_team"],
        f"Reminder: complaint #{complaint['id']} '{complaint['title']}' is past its SLA deadline.",
        complaint["id"],
    )


def escalate_complaint(complaint: dict) -> None:
    """Mark a complaint as Escalated and notify the admins, the team and the student."""
    execute_query(
        "UPDATE complaints SET status = %s, escalated_at = NOW(), updated_at = NOW() WHERE id = %s",
        (STATUS_ESCALATED, complaint["id"]),
    )
    record_history(
        complaint_id=complaint["id"],
        changed_by=None,
        action="escalated",
        old_value=complaint["status"],
        new_value=STATUS_ESCALATED,
        note="Still unresolved after the SLA reminder. Escalated automatically.",
    )
    escalation_message = f"Complaint #{complaint['id']} '{complaint['title']}' was escalated (SLA breached)."
    notify_admins(escalation_message, complaint["id"])
    notify_team_staff(complaint["assigned_team"], escalation_message, complaint["id"])
    notify_users(
        [complaint["student_id"]],
        f"Your complaint #{complaint['id']} has been escalated to the admin team.",
        complaint["id"],
    )


def check_sla_and_escalate(current_time: Optional[datetime] = None) -> dict:
    """Check every overdue complaint once: send reminders or escalate. Returns a summary."""
    current_time = current_time or datetime.now(timezone.utc)
    overdue_complaints = get_overdue_complaints(current_time)
    reminders_sent = 0
    complaints_escalated = 0

    for complaint in overdue_complaints:
        action = decide_sla_action(complaint["sla_due_at"], complaint["reminder_sent_at"], current_time)
        if action == SLA_ACTION_SEND_REMINDER:
            send_sla_reminder(complaint)
            reminders_sent += 1
        elif action == SLA_ACTION_ESCALATE:
            escalate_complaint(complaint)
            complaints_escalated += 1

    return {
        "complaints_checked": len(overdue_complaints),
        "reminders_sent": reminders_sent,
        "complaints_escalated": complaints_escalated,
    }
