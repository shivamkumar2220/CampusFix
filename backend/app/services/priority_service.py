"""Rule-based priority suggestion (Low / Medium / High / Critical).

How it works - every complaint collects "points":
  1. Category base points   (e.g. Wi-Fi is more disruptive than a printer)
  2. Similar open complaints (many people affected = more points)
  3. Keywords               ("urgent", "exam", "lab")
Then the total points are turned into a priority level.
Safety words such as "fire" or "sparking" always give Critical.
Staff can still override the suggested priority.
"""

from app.services.classification_service import contains_keyword

CATEGORY_BASE_POINTS: dict[str, int] = {
    "Network/Wi-Fi": 2,
    "Lab Computer": 2,
    "Electrical": 2,
    "Projector": 2,
    "Printer": 1,
    "Classroom Equipment": 1,
    "General Maintenance": 1,
    "Other": 1,
}

URGENT_KEYWORDS = ["urgent", "emergency", "asap", "immediately"]
EXAM_KEYWORDS = ["exam", "examination", "viva", "practical"]
LAB_KEYWORDS = ["lab", "laboratory"]
SAFETY_KEYWORDS = [
    "fire", "smoke", "spark", "sparking", "shock", "burning",
    "short circuit", "gas leak", "flood", "flooding",
]

URGENT_KEYWORD_POINTS = 2
EXAM_KEYWORD_POINTS = 2
LAB_KEYWORD_POINTS = 1
MANY_SIMILAR_COMPLAINTS_THRESHOLD = 3   # 3+ similar open complaints = widespread problem
MANY_SIMILAR_COMPLAINTS_POINTS = 2
SOME_SIMILAR_COMPLAINTS_POINTS = 1

CRITICAL_MIN_POINTS = 6
HIGH_MIN_POINTS = 4
MEDIUM_MIN_POINTS = 2


def contains_any_keyword(text: str, keywords: list[str]) -> bool:
    """Return True if at least one keyword from the list is in the text."""
    return any(contains_keyword(text, keyword) for keyword in keywords)


def get_points_for_similar_complaints(similar_complaint_count: int) -> int:
    """Give extra points when other students reported the same problem."""
    if similar_complaint_count >= MANY_SIMILAR_COMPLAINTS_THRESHOLD:
        return MANY_SIMILAR_COMPLAINTS_POINTS
    if similar_complaint_count >= 1:
        return SOME_SIMILAR_COMPLAINTS_POINTS
    return 0


def calculate_priority_points(category: str, complaint_text: str, similar_complaint_count: int) -> int:
    """Add up all priority points for a complaint."""
    total_points = CATEGORY_BASE_POINTS.get(category, 1)
    total_points += get_points_for_similar_complaints(similar_complaint_count)

    if contains_any_keyword(complaint_text, URGENT_KEYWORDS):
        total_points += URGENT_KEYWORD_POINTS
    if contains_any_keyword(complaint_text, EXAM_KEYWORDS):
        total_points += EXAM_KEYWORD_POINTS
    if contains_any_keyword(complaint_text, LAB_KEYWORDS):
        total_points += LAB_KEYWORD_POINTS

    return total_points


def convert_points_to_priority(total_points: int) -> str:
    """Turn a points total into a priority level."""
    if total_points >= CRITICAL_MIN_POINTS:
        return "Critical"
    if total_points >= HIGH_MIN_POINTS:
        return "High"
    if total_points >= MEDIUM_MIN_POINTS:
        return "Medium"
    return "Low"


def suggest_priority(
    category: str,
    title: str,
    description: str,
    location: str,
    similar_complaint_count: int,
) -> str:
    """Suggest a priority for a new complaint using the rules above."""
    complaint_text = f"{title} {description} {location}"

    if contains_any_keyword(complaint_text, SAFETY_KEYWORDS):
        return "Critical"

    total_points = calculate_priority_points(category, complaint_text, similar_complaint_count)
    return convert_points_to_priority(total_points)
