"""Simple statistics for the admin dashboard."""

from typing import Optional

from app.constants import FINISHED_STATUSES, STATUS_ESCALATED
from app.database import fetch_all_rows, fetch_one_row


def count_complaints_grouped_by(column_name: str) -> dict[str, int]:
    """Count complaints per value of one column, e.g. {'Open': 4, 'Closed': 2}.

    column_name always comes from our own code (never from the user), so it is safe in the SQL.
    """
    allowed_columns = ("status", "priority", "category", "assigned_team")
    if column_name not in allowed_columns:
        raise ValueError(f"Cannot group by column: {column_name}")
    rows = fetch_all_rows(
        f"SELECT {column_name} AS group_value, COUNT(*) AS complaint_count "
        f"FROM complaints GROUP BY {column_name} ORDER BY complaint_count DESC"
    )
    return {row["group_value"]: row["complaint_count"] for row in rows}


def get_average_resolution_hours() -> Optional[float]:
    """Average hours from creation to resolution, for resolved or closed complaints."""
    row = fetch_one_row(
        """
        SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600) AS average_hours
        FROM complaints
        WHERE resolved_at IS NOT NULL
        """
    )
    if row is None or row["average_hours"] is None:
        return None
    return round(float(row["average_hours"]), 1)


def get_dashboard_stats() -> dict:
    """Collect all numbers shown on the admin dashboard."""
    complaints_by_status = count_complaints_grouped_by("status")
    total_complaints = sum(complaints_by_status.values())
    finished_count = sum(complaints_by_status.get(status_name, 0) for status_name in FINISHED_STATUSES)
    total_users_row = fetch_one_row("SELECT COUNT(*) AS user_count FROM users")

    return {
        "total_complaints": total_complaints,
        "open_complaints": total_complaints - finished_count,
        "escalated_complaints": complaints_by_status.get(STATUS_ESCALATED, 0),
        "resolved_or_closed_complaints": finished_count,
        "total_users": total_users_row["user_count"] if total_users_row else 0,
        "average_resolution_hours": get_average_resolution_hours(),
        "complaints_by_status": complaints_by_status,
        "complaints_by_priority": count_complaints_grouped_by("priority"),
        "complaints_by_category": count_complaints_grouped_by("category"),
        "complaints_by_team": count_complaints_grouped_by("assigned_team"),
    }
