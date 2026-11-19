"""Pydantic models for in-app notifications."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """One in-app notification."""

    id: int
    user_id: int
    complaint_id: Optional[int] = None
    message: str
    is_read: bool
    created_at: datetime
