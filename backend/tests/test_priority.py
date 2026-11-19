"""Tests for the rule-based priority suggestion."""

from app.services.priority_service import convert_points_to_priority, suggest_priority


def test_simple_projector_problem_is_medium() -> None:
    """Projector (2 points) with no keywords -> Medium."""
    assert suggest_priority("Projector", "Projector broken", "No image shown", "Room 204", 0) == "Medium"


def test_printer_problem_is_low() -> None:
    """Printer (1 point) with no keywords -> Low."""
    assert suggest_priority("Printer", "Printer jam", "Paper is stuck", "Library", 0) == "Low"


def test_lab_keyword_raises_priority() -> None:
    """Wi-Fi (2) + 'lab' (1) = 3 points -> Medium."""
    assert suggest_priority("Network/Wi-Fi", "Wi-Fi down", "No internet", "Lab 3", 0) == "Medium"


def test_urgent_keyword_gives_high() -> None:
    """Wi-Fi (2) + 'urgent' (2) = 4 points -> High."""
    assert suggest_priority("Network/Wi-Fi", "Wi-Fi down", "Urgent please fix", "Room 1", 0) == "High"


def test_exam_urgent_and_lab_gives_critical() -> None:
    """Lab Computer (2) + exam (2) + urgent (2) + lab (1) = 7 points -> Critical."""
    priority = suggest_priority(
        "Lab Computer", "PC not working", "We have an exam tomorrow, urgent", "Lab 1", 0
    )
    assert priority == "Critical"


def test_many_similar_complaints_raise_priority() -> None:
    """The same problem reported by 3+ students is more important."""
    without_similar = suggest_priority("Projector", "Projector broken", "No image", "Room 204", 0)
    with_many_similar = suggest_priority("Projector", "Projector broken", "No image", "Room 204", 3)
    assert without_similar == "Medium"
    assert with_many_similar == "High"


def test_safety_keyword_is_always_critical() -> None:
    """Fire or sparking is always Critical, whatever the other points are."""
    assert suggest_priority("Electrical", "Socket sparking", "Sparks from socket", "Room 9", 0) == "Critical"
    assert suggest_priority("Other", "Smoke", "Smoke near the stairs", "Block A", 0) == "Critical"


def test_points_to_priority_boundaries() -> None:
    """Check the exact point limits for every level."""
    assert convert_points_to_priority(1) == "Low"
    assert convert_points_to_priority(2) == "Medium"
    assert convert_points_to_priority(4) == "High"
    assert convert_points_to_priority(6) == "Critical"
