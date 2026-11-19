"""Find similar open complaints (same category + same location).

When several students report the same thing in the same place, it is probably
ONE problem (a "Possible Common Incident"). The system only marks them;
staff verify and group them by hand.
"""

from typing import Optional

from app.constants import FINISHED_STATUSES
from app.database import execute_query, fetch_all_rows


def normalize_location(location: str) -> str:
    """Make locations comparable: ' Lab  3 ' and 'lab 3' both become 'lab 3'."""
    return " ".join(location.lower().split())


def find_similar_open_complaints(
    category: str,
    location: str,
    exclude_complaint_id: Optional[int] = None,
) -> list[dict]:
    """Return open complaints with the same category and location (optionally skipping one id)."""
    query = r"""
        SELECT id, title, status, priority, location, incident_group_id, created_at
        FROM complaints
        WHERE category = %s
          AND LOWER(REGEXP_REPLACE(TRIM(location), '\s+', ' ', 'g')) = %s
          AND status NOT IN (%s, %s)
          AND id <> %s
        ORDER BY created_at
    """
    parameters = (
        category,
        normalize_location(location),
        FINISHED_STATUSES[0],
        FINISHED_STATUSES[1],
        exclude_complaint_id or 0,
    )
    return fetch_all_rows(query, parameters)


def mark_as_possible_common_incident(complaint_ids: list[int]) -> None:
    """Flag the given complaints as a 'Possible Common Incident'."""
    if not complaint_ids:
        return
    execute_query(
        "UPDATE complaints SET is_possible_common_incident = TRUE, updated_at = NOW() WHERE id = ANY(%s)",
        (complaint_ids,),
    )
