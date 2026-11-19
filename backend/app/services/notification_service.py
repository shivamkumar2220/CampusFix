"""Simple in-app notifications stored in the notifications table (no email)."""

from typing import Optional

from fastapi import HTTPException, status

from app.database import execute_query, fetch_all_rows, fetch_one_row, get_connection

MAX_NOTIFICATIONS_RETURNED = 50


def notify_users(user_ids: list[int], message: str, complaint_id: Optional[int] = None) -> None:
    """Create the same notification for several users at once."""
    unique_user_ids = sorted(set(user_ids))
    if not unique_user_ids:
        return
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO notifications (user_id, complaint_id, message) VALUES (%s, %s, %s)",
                [(user_id, complaint_id, message) for user_id in unique_user_ids],
            )


def notify_team_staff(team: str, message: str, complaint_id: Optional[int] = None) -> None:
    """Notify every active staff member of a team (IT or Maintenance)."""
    staff_rows = fetch_all_rows(
        "SELECT id FROM users WHERE role = 'staff' AND team = %s AND is_active = TRUE",
        (team,),
    )
    notify_users([row["id"] for row in staff_rows], message, complaint_id)


def notify_admins(message: str, complaint_id: Optional[int] = None) -> None:
    """Notify every active admin."""
    admin_rows = fetch_all_rows("SELECT id FROM users WHERE role = 'admin' AND is_active = TRUE")
    notify_users([row["id"] for row in admin_rows], message, complaint_id)


def get_notifications_for_user(user_id: int) -> list[dict]:
    """Return the newest notifications of a user."""
    return fetch_all_rows(
        """
        SELECT * FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (user_id, MAX_NOTIFICATIONS_RETURNED),
    )


def mark_notification_as_read(notification_id: int, user_id: int) -> dict:
    """Mark one of the user's own notifications as read (404 if it is not theirs)."""
    updated_notification = fetch_one_row(
        "UPDATE notifications SET is_read = TRUE WHERE id = %s AND user_id = %s RETURNING *",
        (notification_id, user_id),
    )
    if updated_notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return updated_notification


def mark_all_notifications_as_read(user_id: int) -> int:
    """Mark all of the user's notifications as read and return how many changed."""
    return execute_query(
        "UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND is_read = FALSE",
        (user_id,),
    )
