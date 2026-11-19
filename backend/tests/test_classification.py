"""Tests for keyword classification and team assignment."""

import pytest

from app.services.classification_service import (
    classify_complaint,
    contains_keyword,
    get_team_for_category,
)


@pytest.mark.parametrize(
    ("title", "description", "expected_category"),
    [
        ("Wi-Fi not working in Lab 3", "Cannot connect to the internet", "Network/Wi-Fi"),
        ("Network down", "The LAN cable in room 12 is not working", "Network/Wi-Fi"),
        ("Projector broken", "The projector shows no image", "Projector"),
        ("AC not cooling", "The AC in the seminar hall is warm", "Electrical"),
        ("Fans and lights off", "No fan or light works in Room 5", "Electrical"),
        ("Printer jam", "The printer in the library keeps jamming", "Printer"),
        ("PC not booting", "Computer number 12 shows a blue screen", "Lab Computer"),
        ("Smart board issue", "The smart board does not respond to touch", "Classroom Equipment"),
        ("Leaking tap", "Water leaking from the washroom tap", "General Maintenance"),
        ("Something strange", "Nothing here matches any rule", "Other"),
    ],
)
def test_classify_complaint(title: str, description: str, expected_category: str) -> None:
    """Each sample complaint is put in the expected category."""
    assert classify_complaint(title, description) == expected_category


def test_keyword_matching_uses_whole_words() -> None:
    """'ac' must not match inside 'access', and 'lan' must not match inside 'plan'."""
    assert contains_keyword("No access to the portal", "ac") is False
    assert contains_keyword("Our lesson plan", "lan") is False
    assert contains_keyword("The AC is off", "ac") is True


def test_keyword_matching_allows_plural() -> None:
    """'lights' should match the keyword 'light'."""
    assert contains_keyword("All lights are off", "light") is True


@pytest.mark.parametrize(
    ("category", "expected_team"),
    [
        ("Network/Wi-Fi", "IT"),
        ("Projector", "IT"),
        ("Printer", "IT"),
        ("Lab Computer", "IT"),
        ("Electrical", "Maintenance"),
        ("General Maintenance", "Maintenance"),
    ],
)
def test_team_assignment(category: str, expected_team: str) -> None:
    """Each category goes to the right team."""
    assert get_team_for_category(category) == expected_team
