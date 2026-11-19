"""Routes for the logged-in user's in-app notifications."""

from fastapi import APIRouter, Depends

from app.schemas.dashboard_schemas import MessageResponse
from app.schemas.notification_schemas import NotificationResponse
from app.security.role_checker import get_current_user
from app.services import notification_service

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
def get_my_notifications(current_user: dict = Depends(get_current_user)) -> list[dict]:
    """Any role: my newest notifications."""
    return notification_service.get_notifications_for_user(current_user["id"])


@router.patch("/read-all", response_model=MessageResponse)
def mark_all_as_read(current_user: dict = Depends(get_current_user)) -> dict:
    """Any role: mark all my notifications as read."""
    changed_count = notification_service.mark_all_notifications_as_read(current_user["id"])
    return {"message": f"{changed_count} notification(s) marked as read."}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(notification_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    """Any role: mark one of my notifications as read."""
    return notification_service.mark_notification_as_read(notification_id, current_user["id"])
