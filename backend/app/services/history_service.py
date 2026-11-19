"""Saves every change to a complaint in the complaint_history table (who, what, when)."""

from typing import Optional

from app.database import execute_query, fetch_all_rows


def record_history(
    complaint_id: int,
    changed_by: Optional[int],
    action: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    """Add one entry to a complaint's timeline. changed_by=None means the system did it."""
    execute_query(
        """
        INSERT INTO complaint_history (complaint_id, changed_by, action, old_value, new_value, note)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (complaint_id, changed_by, action, old_value, new_value, note),
    )


def get_history_for_complaint(complaint_id: int) -> list[dict]:
    """Return the full timeline of a complaint, oldest first, with the name of who made each change."""
    return fetch_all_rows(
        """
        SELECT h.*, u.full_name AS changed_by_name
        FROM complaint_history h
        LEFT JOIN users u ON u.id = h.changed_by
        WHERE h.complaint_id = %s
        ORDER BY h.created_at, h.id
        """,
        (complaint_id,),
    )
