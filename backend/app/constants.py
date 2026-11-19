"""Fixed values used across the app (they match the CHECK constraints in database/schema.sql)."""

from typing import Literal

# ----- Types used by Pydantic to reject any other value automatically -----
RoleName = Literal["student", "staff", "admin"]
TeamName = Literal["IT", "Maintenance"]
PriorityLevel = Literal["Low", "Medium", "High", "Critical"]
ComplaintStatus = Literal["Open", "In Progress", "Need More Info", "Resolved", "Closed", "Escalated"]
CategoryName = Literal[
    "Network/Wi-Fi",
    "Projector",
    "Lab Computer",
    "Printer",
    "Classroom Equipment",
    "Electrical",
    "General Maintenance",
    "Other",
]

# ----- Status names (use these instead of typing the text again) -----
STATUS_OPEN = "Open"
STATUS_IN_PROGRESS = "In Progress"
STATUS_NEED_MORE_INFO = "Need More Info"
STATUS_RESOLVED = "Resolved"
STATUS_CLOSED = "Closed"
STATUS_ESCALATED = "Escalated"

# Complaints in these statuses are finished and no longer "open"
FINISHED_STATUSES = (STATUS_RESOLVED, STATUS_CLOSED)

# ----- Teams -----
TEAM_IT = "IT"
TEAM_MAINTENANCE = "Maintenance"
